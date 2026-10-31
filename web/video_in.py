# Vídeo enviado com a música: tira o áudio (MP3) e confere se há faixa de som. O ffmpeg já é exigido pelo projeto.
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from web.jobs import UPLOADS


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"{name} não encontrado no PATH")
    return path


def has_audio(video: Path) -> bool:
    """True se o vídeo tem pelo menos uma faixa de áudio."""
    out = subprocess.run([_tool("ffprobe"), "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    if out.returncode != 0:  # arquivo que o ffprobe não entende não é um vídeo
        raise ValueError("o arquivo enviado não é um vídeo MP4 válido")
    return bool(out.stdout.strip())


def extract_audio(video: Path, mp3: Path) -> None:
    """Grava o som do vídeo como MP3 (192 kbps), sem o vídeo."""
    subprocess.run([_tool("ffmpeg"), "-y", "-loglevel", "error", "-i", str(video), "-vn",
                    "-c:a", "libmp3lame", "-b:a", "192k", str(mp3)], check=True)


def prepare_video(video_bytes: bytes, folder: Path, fmt: str) -> tuple[bytes, Path]:
    """Vídeo enviado com a música: devolve o MP3 do som e o caminho do corte no formato pedido (sem som)."""
    from engine import image  # import tardio: a checagem de envio não precisa do motor
    source = folder / "video-original.mp4"
    source.write_bytes(video_bytes)
    if not has_audio(source):
        raise ValueError("o vídeo não tem faixa de som: envie um vídeo com a música ou um MP3")
    mp3 = folder / "musica-do-video.mp3"
    extract_audio(source, mp3)
    width, height = image.SIZES[fmt]
    cut = folder / f"fundo-{fmt}.mp4"
    image.crop_video(source, cut, width, height)
    return mp3.read_bytes(), cut


def create_from_video(queue, data: bytes, filename: str, lyrics: str, style: str, background: str, clip, cuts,
                      video_format: str, texts) -> dict:
    """Vídeo com a música: o som vira o MP3 do job e o vídeo cortado no formato vira o fundo. Um job por formato do atalho."""
    folder = UPLOADS / uuid4().hex  # pasta do envio (a fila limpa as antigas)
    folder.mkdir(parents=True)
    try:
        mp3_bytes, cut = prepare_video(data, folder, video_format)
    except ValueError as error:
        raise HTTPException(400, str(error))
    except RuntimeError as error:  # ffmpeg ausente ou falha do ffmpeg
        raise HTTPException(500, f"não consegui preparar o vídeo: {error}")
    job = queue.create(Path(filename).stem + ".mp3", mp3_bytes, lyrics, style, "video", clip, cuts,
                       (cut.read_bytes(), ".mp4"), video_format, texts)
    return {"id": job.id}
