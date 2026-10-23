# Músicas de uma pasta sincronizada (Google Drive para computador): uma subpasta por música, com um MP3, um TXT e uma imagem opcional.
from pathlib import Path

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


def list_songs(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(folder.name for folder in root.iterdir() if folder.is_dir() and song_files(folder) is not None)


def load_song(root: Path, name: str) -> tuple[bytes, str, tuple[bytes, str] | None] | None:
    """MP3, letra e (imagem, extensão) de uma música da pasta. None = não encontrada ou nome que sai da pasta."""
    folder = root / name
    if folder.resolve().parent != root.resolve() or not folder.is_dir():  # "..", barras e vazio ficam de fora
        return None
    files = song_files(folder)
    if files is None:
        return None
    mp3, text, image = files
    picture = (image.read_bytes(), image.suffix.lower()) if image else None
    return mp3.read_bytes(), text.read_text(encoding="utf-8"), picture
