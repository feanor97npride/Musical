# Informações para postar (títulos, descrição, legenda e hashtags) geradas junto com a letra.
import re

LIMITS = {  # shortcut: limites de texto chutados, subir se a plataforma aceitar mais
    "youtube_title": 100,
    "youtube_description": 1000,
    "tiktok_caption": 150,
}
TAG_RANGE = (3, 6)
TAG = re.compile(r"#\S+")
LABELS = {
    "youtube_title": "Título (YouTube)",
    "youtube_description": "Descrição (YouTube)",
    "tiktok_caption": "Legenda (TikTok)",
}


def posting_problems(data: dict) -> list[str]:
    problems = [f"{field} com mais de {limit} caracteres" for field, limit in LIMITS.items() if len(data[field].strip()) > limit]
    tags = data.get("hashtags")
    low, high = TAG_RANGE
    if not (isinstance(tags, list) and low <= len(tags) <= high and all(isinstance(t, str) and TAG.fullmatch(t) for t in tags)):
        problems.append(f"hashtags fora do formato: de {low} a {high}, cada uma com # e sem espaço")
    return problems


def posting_text(draft: dict) -> str:
    lines = [f"{label}: {draft[field]}" for field, label in LABELS.items()]
    lines.append("Hashtags: " + " ".join(draft["hashtags"]))
    return "\n".join(lines) + "\n"


SECTION_NAMES = {"intro": "Intro", "verse": "Estrofe", "chorus": "Refrão", "bridge": "Ponte", "outro": "Outro"}


def chapters(song: dict) -> str:
    """Capítulos do YouTube: uma linha por troca de seção, com o tempo do primeiro verso (o primeiro começa em 00:00)."""
    lines, section = [], None
    for line in song["lines"]:
        if line["section"] == section:
            continue
        section = line["section"]
        seconds = int(line["start"]) if lines else 0
        minutes, rest = divmod(seconds, 60)
        lines.append(f"{minutes:02d}:{rest:02d} {SECTION_NAMES.get(section, 'Trecho')}")
    return "\n".join(lines)


def with_part(text: str, index: int, total: int, limit: int) -> str:
    """Prefixo 'Parte X/N · ' na frente, com o texto cortado para caber no limite (o prefixo fica inteiro)."""
    prefix = f"Parte {index}/{total} · " if total > 1 else ""
    return (prefix + text[: limit - len(prefix)]).rstrip()


def parts_text(names: list[str], song: dict, draft: dict | None) -> str:
    """postar.txt do pacote: um bloco por arquivo e, no fim, a descrição do YouTube com os capítulos."""
    total = len(names)
    blocks = []
    for index, name in enumerate(names, 1):
        lines = [f"Arquivo: {name}"]
        if draft:  # sem os textos da letra, o bloco traz só o nome do arquivo
            lines += [f"Título: {with_part(draft['youtube_title'], index, total, LIMITS['youtube_title'])}",
                      f"Legenda: {with_part(draft['tiktok_caption'], index, total, LIMITS['tiktok_caption'])}",
                      "Hashtags: " + " ".join(draft["hashtags"])]
        blocks.append("\n".join(lines))
    description = "\n\n".join(part for part in [draft and draft["youtube_description"], chapters(song)] if part)
    if description:
        blocks.append("Descrição do YouTube (com capítulos):\n" + description)
    return "\n\n".join(blocks) + "\n"
