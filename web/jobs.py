# Fila de jobs em memória: um por vez, cada um roda a pipeline num subprocess e lê o progresso do stdout.
import json
import logging
import os
import queue
import re
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from engine.cuts import plan_cuts
from engine.names import clean_name, make_slug, variant_name
from engine.pipeline import OUTPUT, ROOT

UPLOADS = ROOT / "output" / "web"
STAGE_LINE = re.compile(r"^\[(\d+)/(\d+)\] (.+?)\.\.\.")
ERROR_LINE = re.compile(r"^erro: (.+)")
FRAME_LINE = re.compile(r"Rendered (\d+)/(\d+)")
PATH_IN_TEXT = re.compile(r"(?<![\w.])(?:[A-Za-z]:)?[\\/]\S*")  # caminho do PC: não vai para o navegador
logger = logging.getLogger(__name__)


def hide_paths(text: str) -> str:
    return PATH_IN_TEXT.sub("<caminho>", text)


@dataclass
class Job:
    id: str
    folder: Path
    audio: Path  # o nome do arquivo vira o nome da pasta de saída, por isso leva o nome da música
    style: str
    background: str
    clip: tuple[float, float] | None
    video: Path | None = None
    status: str = "queued"
    stage: str = "Na fila"
    message: str = ""
    cuts: int | None = None  # segundos por corte; None = um vídeo só
    ready_videos: list[Path] = field(default_factory=list)  # guardados quando o job termina
    step: int = 0  # etapa atual e total, lidos de "[3/7] ..." na saída da pipeline
    total: int = 0
    progress: float = 0.0  # de 0 a 1; nunca diminui (os cortes renderizam um depois do outro)
    background_image: Path | None = None  # imagem enviada pelo usuário; só vale com fundo "image"
    format: str = "vertical"  # "horizontal" = 16:9 para o YouTube

    @property
    def lyrics(self) -> Path:
        return self.folder / "lyrics.txt"

    @property
    def videos(self) -> list[Path]:
        """Arquivos prontos do job: um por corte, ou o vídeo único."""
        if not self.cuts:
            return [self.video]
        song = json.loads((self.video.parent / "song.json").read_text(encoding="utf-8"))
        return [self.video.parent / f"video-{variant_name(self.style, self.background, clip, self.format)}.mp4"
                for clip in plan_cuts(song, self.cuts)]

    def read_line(self, line: str) -> None:
        stage = STAGE_LINE.match(line)
        if stage:
            self.step, self.total, self.stage, self.message = int(stage.group(1)), int(stage.group(2)), stage.group(3), ""
            self._advance(self.step - 1)
        error = ERROR_LINE.match(line)
        if error:
            self.message = hide_paths(error.group(1))
        frame = FRAME_LINE.search(line)
        if frame:
            self.message = f"quadro {frame.group(1)} de {frame.group(2)}"
            if int(frame.group(2)):
                self._advance(self.step - 1 + int(frame.group(1)) / int(frame.group(2)))

    def _advance(self, steps_done: float) -> None:
        if self.total:
            self.progress = max(self.progress, min(steps_done / self.total, 1.0))

    def to_dict(self) -> dict:
        data = {"status": self.status, "stage": self.stage, "message": self.message,
                "step": self.step, "total": self.total, "progress": round(self.progress, 3)}
        if self.status == "done":
            data["videos"] = [path.name for path in self.ready_videos]
        return data


def run_pipeline(job: Job) -> int:
    command = [sys.executable, "-m", "engine.pipeline", "--audio", str(job.audio),
               "--lyrics", str(job.lyrics), "--style", job.style, "--background", job.background,
               "--format", job.format]
    if job.clip:
        command += ["--clip", f"{job.clip[0]}:{job.clip[1]}"]
    if job.cuts:
        command += ["--cuts", str(job.cuts)]
    if job.background == "image":
        command += ["--background-image", str(job.background_image)]
    # no Windows o filho escreve em cp1252 por padrão; forçamos UTF-8 para o texto com acento não quebrar a leitura
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               encoding="utf-8", errors="replace",
                               env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"})
    for line in process.stdout:
        job.read_line(line.rstrip("\r\n"))
    return process.wait()


class JobQueue:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self._pending: queue.Queue[Job] = queue.Queue()
        self._worker: threading.Thread | None = None

    def create(self, filename: str, audio: bytes, lyrics: str, style: str, background: str,
               clip: tuple[float, float] | None, cuts: int | None = None,
               image: tuple[bytes, str] | None = None, fmt: str = "vertical") -> Job:
        job_id = uuid.uuid4().hex
        folder = UPLOADS / job_id
        folder.mkdir(parents=True)
        job = Job(job_id, folder, folder / f"{clean_name(Path(filename).stem)}.mp3", style, background, clip,
                  cuts=cuts, format=fmt)
        job.audio.write_bytes(audio)
        if image:  # a imagem fica na pasta do job, com a extensão que o usuário enviou
            job.background_image = folder / f"fundo{image[1]}"
            job.background_image.write_bytes(image[0])
        job.lyrics.write_text(lyrics, encoding="utf-8", newline="")  # no Windows, sem isso cada \n vira \r\n
        # lê o arquivo de volta: o navegador manda \r\n e o pipeline normaliza, o nome da pasta tem que bater
        slug = make_slug(job.audio, job.lyrics.read_text(encoding="utf-8"))
        job.video = OUTPUT / slug / f"video-{variant_name(style, background, clip, fmt)}.mp4"
        self.jobs[job_id] = job
        self._pending.put(job)
        return job

    def start(self) -> None:
        if self._worker is None:  # uma thread só: um job de cada vez
            self._worker = threading.Thread(target=self._work, daemon=True)
            self._worker.start()

    def _work(self) -> None:
        while True:
            self._execute(self._pending.get())

    def _execute(self, job: Job) -> None:
        job.status = "running"
        try:
            code = run_pipeline(job)
            ready = code == 0 and all(path.exists() for path in job.videos)  # lê o song.json dos cortes
            if ready:
                job.ready_videos = job.videos  # guarda a lista: depois o song.json pode não estar mais lá
        except Exception:  # a pipeline nem chegou a rodar, ou o song.json não está lá
            logger.exception("erro inesperado no job %s", job.id)  # o detalhe com caminhos fica no terminal
            code, ready, job.message = 1, False, "erro inesperado no servidor; veja a janela do iniciador"
        if ready:
            job.status, job.stage, job.message, job.progress = "done", "Concluído", "", 1.0
        else:
            job.message = job.message or f"a pipeline terminou com código {code}"  # antes do status: o polling para em error
            job.status = "error"
