# Drive automático: uma thread olha a pasta de entrada e gera sozinha as músicas que aparecem ou mudam.
import json
import logging
import os
import time
from pathlib import Path

from engine.pipeline import OUTPUT
from web import limites, telegram
from web.jobs import MAX_PENDING, JobQueue, QueueFull
from web.library import IMAGE_SUFFIXES, load_song, lone_mp3, song_files

logger = logging.getLogger(__name__)
STATE = OUTPUT / "drive-auto.json"  # fora do Git: nome da pasta -> assinatura dos arquivos já processados
# espelha web/static/presets.js: (formato, segundos por corte; None = vídeo inteiro)
PRESETS = {"full": [("horizontal", None), ("vertical", 90)], "tiktok": [("vertical", 90)], "yt": [("horizontal", None)]}
DEFAULT_INTERVAL = 60  # segundos entre uma varredura e outra
MIN_INTERVAL = 5


def enabled() -> bool:
    return os.environ.get("DRIVE_AUTO", "").strip().lower() in ("1", "true", "sim", "yes")


def song_paths(folder: Path) -> list[Path] | None:
    """Arquivos que definem a música: MP3, TXT (se houver) e a primeira imagem. None se a pasta não é uma música válida."""
    files = song_files(folder)
    if files is not None:
        return [path for path in files if path is not None]
    mp3 = lone_mp3(folder)  # sem TXT: a letra vem da transcrição
    if mp3 is None:
        return None
    images = sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
    return [mp3, *images[:1]]


def signature(folder: Path) -> str | None:
    """Nome, tamanho e data de cada arquivo da música. None se a pasta não é uma música válida ou há arquivo vazio."""
    files = song_paths(folder)
    if files is None:
        return None
    parts = []
    for path in files:
        stat = path.stat()
        if stat.st_size == 0:  # o Drive ainda está gravando o arquivo
            return None
        parts.append(f"{path.name}:{stat.st_size}:{int(stat.st_mtime)}")
    return "|".join(parts)


def load_state() -> dict[str, str] | None:
    """None quando o arquivo não existe ou está quebrado: a primeira varredura só registra o que já está na pasta."""
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def save_state(state: dict[str, str]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE)


def current(root: Path) -> dict[str, str]:
    """Assinatura de cada música válida da pasta de entrada."""
    found = {folder.name: signature(folder) for folder in sorted(root.iterdir()) if folder.is_dir()}
    return {name: sig for name, sig in found.items() if sig}


def create_jobs(queue: JobQueue, root: Path, name: str, preset: str) -> None:
    """Um job por formato do atalho. ValueError = música que não dá para gerar (grande demais, letra vazia)."""
    song = load_song(root, name)
    if song is None:
        raise ValueError("a pasta precisa de exatamente um MP3 e um TXT")
    audio, lyrics, image = song
    if not lyrics.strip():
        raise ValueError("a letra da pasta está vazia")
    background = "image" if image else "gradient"
    for video_format, cuts in PRESETS[preset]:
        queue.create(f"{name}.mp3", audio, lyrics, "karaoke", background, None, cuts, image, video_format, library_name=name)


def start_transcription(queue: JobQueue, root: Path, name: str, sig: str, transcribing: dict) -> None:
    """Pasta só com MP3: cria o job que transcreve a letra pelo áudio. ValueError = MP3 grande demais."""
    mp3 = lone_mp3(root / name)
    if mp3 is None:
        raise ValueError("a pasta mudou: não tem mais só um MP3")
    if mp3.stat().st_size > limites.MAX_BYTES:
        raise ValueError(f"o MP3 passa do limite de {limites.MAX_BYTES // (1024 * 1024)} MB")
    transcribing[name] = (queue.create_letra(f"{name}.mp3", mp3.read_bytes()), sig)


def finish_transcriptions(root: Path, state: dict[str, str], transcribing: dict) -> None:
    """Job de transcrição pronto: grava o letra.txt na pasta, que passa a ser uma música normal. Com erro: avisa e não repete."""
    for name, (job, sig) in list(transcribing.items()):
        if job.status not in ("done", "error"):
            continue
        del transcribing[name]
        try:
            text = job.transcript.read_text(encoding="utf-8") if job.status == "done" else ""
            if text.strip():
                (root / name / "letra.txt").write_text(text, encoding="utf-8", newline="")  # newline="": sem \r\n extra no Windows
                logger.info("Drive automático: letra de %s gravada em letra.txt", name)
                continue
        except OSError:
            logger.warning("Drive automático não conseguiu gravar o letra.txt de %s", name)
        reason = job.message or "nenhuma fala reconhecida"
        logger.warning("Drive automático não transcreveu %s: %s", name, reason)
        telegram.send(f"Não consegui transcrever a letra de {name}: {reason}")
        state[name] = sig  # não repete até a pasta mudar
        save_state(state)


def scan_once(queue: JobQueue, root: Path, state: dict[str, str], waiting: dict[str, str], preset: str,
              transcribing: dict | None = None) -> None:
    """Gera as músicas novas ou alteradas que ficaram iguais em duas varreduras seguidas (sem TXT, transcreve antes)."""
    transcribing = {} if transcribing is None else transcribing
    finish_transcriptions(root, state, transcribing)
    for name, sig in current(root).items():
        if state.get(name) == sig or name in transcribing:
            continue
        if waiting.get(name) != sig:  # primeira vez que vê esta versão: espera a próxima varredura
            waiting[name] = sig
            continue
        queued = sum(job.status == "queued" for job in queue.jobs.values())
        only_mp3 = song_files(root / name) is None  # sem TXT: o primeiro job é a transcrição
        if queued + (1 if only_mp3 else len(PRESETS[preset])) > MAX_PENDING:  # sem lugar para todos os jobs: tenta no próximo ciclo
            logger.info("fila cheia: %s fica para a próxima varredura", name)
            return
        try:
            if only_mp3:
                start_transcription(queue, root, name, sig, transcribing)
                waiting.pop(name, None)
                logger.info("Drive automático: %s sem TXT, transcrevendo a letra", name)
                continue  # o estado só é salvo quando a transcrição termina
            create_jobs(queue, root, name, preset)
        except QueueFull:
            return
        except ValueError as error:  # não adianta tentar de novo até a pasta mudar
            logger.warning("Drive automático ignorou %s: %s", name, error)
        except OSError:  # o Drive pode estar apagando ou movendo o arquivo agora
            logger.warning("Drive automático não conseguiu ler %s; tenta de novo", name)
            continue
        state[name] = sig
        waiting.pop(name, None)
        save_state(state)
        logger.info("Drive automático: %s na fila (%s)", name, preset)


def watch(queue: JobQueue) -> None:
    root = Path(os.environ.get("DRIVE_INPUT_DIR", "").strip())
    preset = os.environ.get("DRIVE_AUTO_PRESET", "full").strip().lower()
    if preset not in PRESETS:
        logger.error("DRIVE_AUTO_PRESET inválido (%s): use full, tiktok ou yt", preset)
        return
    try:
        interval = max(MIN_INTERVAL, int(os.environ.get("DRIVE_AUTO_INTERVAL", DEFAULT_INTERVAL)))
    except ValueError:
        interval = DEFAULT_INTERVAL
    state: dict[str, str] | None = load_state()
    waiting: dict[str, str] = {}
    transcribing: dict = {}  # pasta -> (job de transcrição, assinatura do MP3 sem letra)
    while True:
        try:
            if root.is_dir():  # Drive desligado: espera ele voltar
                if state is None:  # primeira ativação: só registra o que já existe, sem gerar tudo de uma vez
                    state = current(root)
                    save_state(state)
                    logger.info("Drive automático ligado: %d música(s) já na pasta; só as novas serão geradas", len(state))
                scan_once(queue, root, state, waiting, preset, transcribing)
        except Exception:  # nada pode matar a thread
            logger.exception("erro na varredura do Drive automático")
        time.sleep(interval)
