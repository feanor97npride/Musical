# Parser da letra: versos e marcadores de seção.
import re

SECTION_BY_MARKER = {
    "verso": "verse",
    "verse": "verse",
    "refrão": "chorus",
    "chorus": "chorus",
    "ponte": "bridge",
    "bridge": "bridge",
    "intro": "intro",
    "outro": "outro",
}
MARKER = re.compile(r"\[(.*)\]")


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
            section = SECTION_BY_MARKER.get(marker.group(1).strip().lower(), "other")
            continue
        lines.append({"text": line, "section": section})
    return lines


def flat_text(lines: list[dict]) -> str:
    """Junta os versos em um texto só, um verso por linha, para o alinhador."""
    return "\n".join(line["text"] for line in lines)
