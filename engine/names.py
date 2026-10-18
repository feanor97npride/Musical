# Nomes de pastas e arquivos: o mesmo cálculo serve à linha de comando e à web.
import hashlib
import re
import unicodedata
from pathlib import Path


def clean_name(name: str) -> str:
    stem = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "musica"


def make_slug(audio: Path, lyrics: str) -> str:
    digest = hashlib.sha1(audio.read_bytes() + lyrics.encode("utf-8")).hexdigest()[:8]
    return f"{clean_name(audio.stem)}-{digest}"


def variant_name(style: str, background: str, clip: tuple[float, float] | None) -> str:
    """Estilo, fundo e trecho juntos: cada combinação tem props e vídeo próprios."""
    name = f"{style}-{background}"
    if clip is None:
        return name
    # sem o int, 30.0 viraria "30.0"; com :g, 30.00001 viraria "30" e colidiria com 30.0
    start, end = (int(value) if value.is_integer() else value for value in clip)
    return f"{name}-{start}-{end}"
