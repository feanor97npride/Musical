# Fila de jobs em memória: um por vez, cada um roda a pipeline num subprocess e lê o progresso do stdout.
import os
import queue
import re
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

from engine.pipeline import OUTPUT, ROOT, clean_name, make_slug

UPLOADS = ROOT / "output" / "web"
STAGE_LINE = re.compile(r"^\[\d/\d\] (.+?)\.\.\.")
ERROR_LINE = re.compile(r"^erro: (.+)")
FRAME_LINE = re.compile(r"Rendered (\d+)/(\d+)")


@dataclass
class Job:
    id: str
    folder: Path
    audio: Path  # o nome do arquivo vira o nome da pasta de saída, por isso leva o nome da música
    style: str
    clip: tuple[float, float] | None
    video: Path | None = None
    status: str = "queued"
    stage: str = "Na fila"
    message: str = ""

    @property
    def lyrics(self) -> Path:
        return self.folder / "lyrics.txt"

    def read_line(self, line: str) -> None:
        stage = STAGE_LINE.match(line)
        if stage:
            self.stage, self.message = stage.group(1), ""
        error = ERROR_LINE.match(line)
        if error:
            self.message = error.group(1)
        frame = FRAME_LINE.search(line)
        if frame:
            self.message = f"quadro {frame.group(1)} de {frame.group(2)}"

    def to_dict(self) -> dict:
        return {"status": self.status, "stage": self.stage, "message": self.message}


def run_pipeline(job: Job) -> int:
    command = [sys.executable, "-m", "engine.pipeline", "--audio", str(job.audio),
               "--lyrics", str(job.lyrics), "--style", job.style]
    if job.clip:
        command += ["--clip", f"{job.clip[0]}:{job.clip[1]}"]
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

    def create(self, filename: str, audio: bytes, lyrics: str, style: str, clip: tuple[float, float] | None) -> Job:
        job_id = uuid.uuid4().hex
        folder = UPLOADS / job_id
        folder.mkdir(parents=True)
        job = Job(job_id, folder, folder / f"{clean_name(Path(filename).stem)}.mp3", style, clip)
        job.audio.write_bytes(audio)
        job.lyrics.write_text(lyrics, encoding="utf-8", newline="")  # no Windows, sem isso cada \n vira \r\n
        # lê o arquivo de volta: o navegador manda \r\n e o pipeline normaliza, o nome da pasta tem que bater
        job.video = OUTPUT / make_slug(job.audio, job.lyrics.read_text(encoding="utf-8")) / "video.mp4"
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
        except Exception as error:  # a pipeline nem chegou a rodar
            code, job.message = 1, str(error)
        if code == 0 and job.video.exists():
            job.status, job.stage, job.message = "done", "Concluído", ""
        else:
            job.status = "error"
            job.message = job.message or f"a pipeline terminou com código {code}"
