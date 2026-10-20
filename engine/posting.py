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
    problems = [f"{field} com mais de {limit} caracteres" for field, limit in LIMITS.items() if len(data[field]) > limit]
    tags = data.get("hashtags")
    low, high = TAG_RANGE
    if not (isinstance(tags, list) and low <= len(tags) <= high and all(isinstance(t, str) and TAG.fullmatch(t) for t in tags)):
        problems.append(f"hashtags fora do formato: de {low} a {high}, cada uma com # e sem espaço")
    return problems


def posting_text(draft: dict) -> str:
    lines = [f"{label}: {draft[field]}" for field, label in LABELS.items()]
    lines.append("Hashtags: " + " ".join(draft["hashtags"]))
    return "\n".join(lines) + "\n"
