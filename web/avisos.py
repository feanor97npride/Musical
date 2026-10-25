# Avisos no Telegram quando um vídeo termina: uma thread olha a fila e manda uma mensagem por job.
import os
import time

from web import telegram
from web.jobs import Job, JobQueue

SHAPES = {"vertical": "9:16", "horizontal": "16:9"}


def should_notify(job: Job) -> bool:
    """Só vídeos que terminaram sozinhos. Por padrão só os da pasta do Drive; TELEGRAM_NOTIFY=all avisa todos."""
    if job.kind != "video" or not job.finished or job.cancelled:  # finished só é preenchido no fim do job
        return False
    return job.library_name is not None or os.environ.get("TELEGRAM_NOTIFY", "drive").strip().lower() == "all"


def message(job: Job) -> str:
    name = job.library_name or job.audio.stem
    shape = SHAPES.get(job.format, job.format)
    if job.status == "done":
        text = f"Vídeo pronto: {name} ({shape}, {len(job.ready_videos)} arquivo(s))"
        return f"{text}\n{job.message}" if job.message else text  # a mensagem do job pronto é o aviso da cópia para o Drive
    return f"Erro ao gerar {name} ({shape}): {job.message}"


def notify_new(queue: JobQueue, seen: set[str]) -> None:
    for job in list(queue.jobs.values()):
        if job.id not in seen and should_notify(job):
            seen.add(job.id)
            telegram.send(message(job))


def watch(queue: JobQueue, interval: float = 5.0) -> None:
    seen: set[str] = set()
    while True:
        notify_new(queue, seen)
        time.sleep(interval)
