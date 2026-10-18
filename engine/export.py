# Exporta o vídeo pronto para postar: H.264 em yuv420p, áudio AAC e moov no começo do arquivo.
import argparse
import os
import shutil
import subprocess
from pathlib import Path

from engine.names import clean_name

# shortcut: teto de 8 Mbps e CRF 23 chutados até confirmar as regras do TikTok e do Kwai, ajustar quando confirmar
MAX_RATE = "8M"
BUF_SIZE = "16M"


def export_name(audio: Path, variant: str) -> str:
    """Título sem acento mais a variante (fundo, estilo e trecho), para que variantes não se sobrescrevam."""
    return f"{clean_name(audio.stem)}-{variant}.mp4"


def export(src: Path, dst: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg não encontrado: instale o FFmpeg e confira o PATH")
    tmp = dst.with_suffix(".tmp.mp4")  # um nome por cópia: exportações de variantes diferentes não se misturam
    try:
        subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
                        "-maxrate", MAX_RATE, "-bufsize", BUF_SIZE,
                        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tmp)], check=True)
        os.replace(tmp, dst)  # só troca o arquivo antigo quando o ffmpeg terminou sem erro
    finally:
        tmp.unlink(missing_ok=True)


def export_video(video: Path, audio: Path, variant: str, force: bool) -> str | None:
    """Cópia em para-postar/, ao lado do vídeo. Pula quando a cópia é mais nova que o vídeo e que este arquivo."""
    dst = video.parent / "para-postar" / export_name(audio, variant)
    source = max(video.stat().st_mtime, Path(__file__).stat().st_mtime)  # mudar MAX_RATE aqui refaz as cópias
    if dst.exists() and dst.stat().st_mtime >= source and not force:
        return "pulado (cache)"
    dst.parent.mkdir(exist_ok=True)
    export(video, dst)
    return None


def export_all(args: argparse.Namespace, videos: list[tuple[Path, str]]) -> str | None:
    """Uma cópia por vídeo (cada corte tem o seu). Sem --export, não faz nada."""
    if not args.export:
        return "desligado (sem --export)"
    notes = [export_video(video, args.audio, variant, args.force) for video, variant in videos]
    return "pulado (cache)" if all(notes) else None
