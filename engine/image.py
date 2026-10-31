# Fundo com imagem enviada pelo usuário: corta no centro (9:16 ou 16:9) e reaproveita o corte enquanto a imagem não muda.
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

SIZES = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}


def crop_to(source: Path, target: Path, width: int, height: int) -> None:
    """Corta no centro para width x height e grava em JPEG."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg não encontrado no PATH")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(source), "-vf",
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
                    "-frames:v", "1", str(target)], check=True)


def ensure_background(out: Path, source: Path | None, force: bool, fmt: str = "vertical") -> Path:
    """Devolve o corte da imagem enviada no formato pedido; refaz só se a imagem mudou."""
    if source is None or not source.exists():
        raise RuntimeError("fundo de imagem sem o arquivo enviado (use --background-image)")
    name = "background-16x9" if fmt == "horizontal" else "background"
    target = out / f"{name}.jpg"
    hash_file = out / f"{name}.hash"
    digest = hashlib.sha1(source.read_bytes()).hexdigest()
    if target.exists() and hash_file.exists() and hash_file.read_text(encoding="utf-8") == digest and not force:
        return target
    tmp = out / f"{name}.tmp.jpg"
    try:
        crop_to(source, tmp, *SIZES[fmt])
        os.replace(tmp, target)  # só troca depois que o corte termina, como o vídeo
    finally:
        tmp.unlink(missing_ok=True)
    hash_file.write_text(digest, encoding="utf-8")
    return target


def crop_video(source: Path, target: Path, width: int, height: int) -> None:
    """Corta o vídeo no centro para width x height, sem som (a música vem do MP3), em H.264."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg não encontrado no PATH")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(source), "-an", "-vf",
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "23", str(target)], check=True)
