# Entrega para a pasta de saída do Drive (sincronizada no PC): uma subpasta por música, com os MP4 e o postar.txt.
import os
import shutil
from pathlib import Path

from engine.export import exported_path
from engine.posting import parts_text
from web.jobs import Job
from web.pacote import part_names, song_of


def deliver(job: Job, root: Path) -> Path:
    names = part_names(job)
    dest = root / job.library_name
    dest.mkdir(parents=True, exist_ok=True)
    for video, name in zip(job.ready_videos, names):
        shutil.copyfile(exported_path(video, job.audio), dest / name)
    (dest / "postar.txt").write_text(parts_text(names, song_of(job), job.draft), encoding="utf-8-sig")
    return dest


def deliver_ready(job: Job) -> None:
    """Chamado pela fila quando um job termina bem. Só músicas da pasta do Drive, e só com DRIVE_OUTPUT_DIR preenchido."""
    root = os.environ.get("DRIVE_OUTPUT_DIR", "").strip()
    if job.library_name and root:
        deliver(job, Path(root))
