# Parser da letra: versos e marcadores de seção.
import re
import unicodedata
from pathlib import Path

# chaves sem acento e em minúsculas: "Refrão", "REFRAO" e "refrao" são o mesmo marcador
SECTION_BY_MARKER = {
    "verso": "verse",
    "verse": "verse",
    "estrofe": "verse",
    "refrao": "chorus",
    "chorus": "chorus",
    "coro": "chorus",
    "ponte": "bridge",
    "bridge": "bridge",
    "intro": "intro",
    "instrumental": "intro",
    "outro": "outro",
    "pre-chorus": "verse",
    "pre-refrao": "verse",
    "final chorus": "chorus",
}
MARKER = re.compile(r"\[(.*)\]")


def marker_name(text: str) -> str:
    """Nome do marcador sem acento, em minúsculas e sem o número ("Verse 1" vira "verse")."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"\s*\d+$", "", plain.strip().lower())


def parse_lyrics(text: str) -> list[dict]:
    """Devolve os versos com a seção de cada um. Marcadores em linha própria viram seção."""
    lines: list[dict] = []
    section = "verse"
    for raw in text.lstrip("﻿").splitlines():  # BOM do Windows quebraria o primeiro marcador
        line = raw.strip()
        if not line:
            continue
        marker = MARKER.fullmatch(line)
        if marker:
            section = SECTION_BY_MARKER.get(marker_name(marker.group(1)), "other")
            continue
        lines.append({"text": line, "section": section})
    return lines


def unknown_markers(text: str) -> list[str]:
    """Marcadores em linha própria que o parser não conhece (eles viram seção 'other')."""
    names = (MARKER.fullmatch(raw.strip()) for raw in text.lstrip("﻿").splitlines())
    return [m.group(1) for m in names if m and marker_name(m.group(1)) not in SECTION_BY_MARKER]


def read_lyrics_file(path: Path) -> str:
    """Letra do arquivo, já validada: UTF-8 e com ao menos um verso. Levanta ValueError com a razão."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"não consegui ler a letra: {error}") from error
    if not parse_lyrics(text):
        raise ValueError("a letra não tem versos (só linhas vazias ou marcadores)")
    return text


def flat_text(lines: list[dict]) -> str:
    """Junta os versos em um texto só, um verso por linha, para o alinhador."""
    return "\n".join(line["text"] for line in lines)
