# Músicas de uma pasta sincronizada (Google Drive para computador): uma subpasta por música, com um MP3, um TXT e uma imagem opcional.
from pathlib import Path

from web import limites

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")


def song_files(folder: Path) -> tuple[Path, Path, Path | None] | None:
    """MP3, letra e imagem da pasta; None se não houver exatamente um MP3 e um TXT."""
    files = [path for path in folder.iterdir() if path.is_file()]
    mp3s = [path for path in files if path.suffix.lower() == ".mp3"]
    texts = [path for path in files if path.suffix.lower() == ".txt"]
    if len(mp3s) != 1 or len(texts) != 1:
        return None
    images = sorted(path for path in files if path.suffix.lower() in IMAGE_SUFFIXES)
    return mp3s[0], texts[0], images[0] if images else None


def lone_mp3(folder: Path) -> Path | None:
    """O MP3 de uma pasta que tem só ele (sem TXT): o Drive automático transcreve a letra pelo áudio."""
    files = [path for path in folder.iterdir() if path.is_file()]
    mp3s = [path for path in files if path.suffix.lower() == ".mp3"]
    has_text = any(path.suffix.lower() == ".txt" for path in files)
    return mp3s[0] if len(mp3s) == 1 and not has_text else None


def list_songs(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(folder.name for folder in root.iterdir() if folder.is_dir() and song_files(folder) is not None)


def read_lyrics(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig")  # o BOM some; o Bloco de Notas salva em UTF-8 com BOM às vezes
    except UnicodeDecodeError:  # arquivo salvo em ANSI (cp1252), comum em versões antigas do Bloco de Notas
        return raw.decode("cp1252", errors="replace")


def load_song(root: Path, name: str) -> tuple[bytes, str, tuple[bytes, str] | None] | None:
    """MP3, letra e (imagem, extensão) de uma música da pasta. None = não encontrada ou nome que sai da pasta.
    Levanta ValueError se o MP3 ou a imagem passarem do limite (checado antes de ler o arquivo)."""
    folder = root / name
    if folder.resolve().parent != root.resolve() or not folder.is_dir():  # "..", barras e vazio ficam de fora
        return None
    files = song_files(folder)
    if files is None:
        return None
    mp3, text, image = files
    if mp3.stat().st_size > limites.MAX_BYTES:
        raise ValueError(f"o MP3 passa do limite de {limites.MAX_BYTES // (1024 * 1024)} MB")
    if image and image.stat().st_size > limites.MAX_IMAGE_BYTES:
        raise ValueError(f"a imagem passa do limite de {limites.MAX_IMAGE_BYTES // (1024 * 1024)} MB")
    picture = (image.read_bytes(), image.suffix.lower()) if image else None
    return mp3.read_bytes(), read_lyrics(text), picture
