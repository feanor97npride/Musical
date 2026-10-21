# Fundo com imagem enviada pelo usuário: corta para 1080x1920 (9:16) e reaproveita o corte enquanto a imagem não muda.
import hashlib
import os
import shutil
import subprocess
from pathlib import Path


def crop_to_vertical(source: Path, target: Path) -> None:
    """Corta no centro para 1080x1920 e grava em JPEG."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg não encontrado no PATH")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(source), "-vf",
                    "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                    "-frames:v", "1", str(target)], check=True)


def ensure_background(out: Path, source: Path | None, force: bool) -> Path:
    """Devolve out/background.jpg com a imagem enviada; refaz o corte só se a imagem mudou."""
    if source is None or not source.exists():
        raise RuntimeError("fundo de imagem sem o arquivo enviado (use --background-image)")
    target = out / "background.jpg"
    hash_file = out / "background.hash"
    digest = hashlib.sha1(source.read_bytes()).hexdigest()
    if target.exists() and hash_file.exists() and hash_file.read_text(encoding="utf-8") == digest and not force:
        return target
    tmp = out / "background.tmp.jpg"
    try:
        crop_to_vertical(source, tmp)
        os.replace(tmp, target)  # só troca depois que o corte termina, como o vídeo
    finally:
        tmp.unlink(missing_ok=True)
    hash_file.write_text(digest, encoding="utf-8")
    return target
