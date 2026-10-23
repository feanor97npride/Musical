# Pacote para postar: as cópias exportadas com nomes legíveis e um postar.txt com os textos de cada parte.
import json
import os
import threading
import zipfile
from pathlib import Path

from engine.export import exported_path, part_name
from engine.posting import LIMITS, parts_text, posting_problems
from web.jobs import Job

_PACK_LOCK = threading.Lock()  # dois cliques no mesmo pacote não podem gravar o mesmo .tmp ao mesmo tempo


def parse_draft(text: str) -> dict | None:
    """Textos da letra enviados pelo formulário (opcionais). Recusa o que não passa nas regras de postagem."""
    if not text.strip():
        return None
    draft = json.loads(text)  # JSON inválido também vira ValueError
    if not isinstance(draft, dict) or any(not isinstance(draft.get(field), str) for field in LIMITS):
        raise ValueError("os textos para postar não estão completos")
    problems = posting_problems(draft)
    if problems:
        raise ValueError("; ".join(problems))
    return draft


def part_names(job: Job) -> list[str]:
    """Nome legível de cada parte pronta do job (01-musica-parte-1-de-10.mp4, ou só o título)."""
    total = len(job.ready_videos)
    return [part_name(job.audio, index, total) for index in range(1, total + 1)]


def song_of(job: Job) -> dict:
    """Capítulos e versos do song.json do job; sem o arquivo, lista vazia."""
    song_path = job.video.parent / "song.json"
    return json.loads(song_path.read_text(encoding="utf-8")) if song_path.exists() else {"lines": []}


def build_pack(job: Job) -> Path:
    """pacote.zip na pasta do job. Reaproveita o arquivo se já existe (o job não muda depois de pronto)."""
    zip_path = job.folder / "pacote.zip"
    with _PACK_LOCK:
        if zip_path.exists():
            return zip_path
        names = part_names(job)
        tmp = job.folder / "pacote.zip.tmp"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as archive:  # MP4 já é comprimido: sem compactar é mais rápido
            for video, name in zip(job.ready_videos, names):
                archive.write(exported_path(video, job.audio), arcname=name)
            # BOM: o Bloco de Notas do Windows lê os acentos corretamente
            archive.writestr("postar.txt", parts_text(names, song_of(job), job.draft).encode("utf-8-sig"))
        os.replace(tmp, zip_path)
    return zip_path
