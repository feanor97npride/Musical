# Tema do vídeo: default_theme(), analyze_theme() via Claude API e CLI que grava o theme no song.json.
import argparse
import json
import os
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from engine.checks import FONTS
from engine.lyrics import flat_text
from engine.schema import Theme, validate_song

ROOT = Path(__file__).resolve().parents[1]
MODEL_DEFAULT = "claude-haiku-5-5"
HEX6 = re.compile(r"#[0-9A-Fa-f]{6}")
FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")
SYSTEM = (
    "Responda APENAS com um JSON, sem texto antes ou depois, sem cercas de código. "
    "Campos: title (texto), mood (texto), keywords (de 3 a 6 textos), palette (de 3 a 5 cores "
    "#RRGGBB, da mais escura para a mais clara), font (uma de: " + ", ".join(sorted(FONTS)) + "), "
    "visual_concept (uma frase)."
)


def default_theme() -> Theme:
    return Theme(
        title="Padrão",
        mood="neutro",
        keywords=["neutro"],
        palette=["#111111", "#1E1E24", "#3A3A44"],
        font="Inter",
        visual_concept="Fundo escuro e neutro",
    )


def analyze_theme(lines_text: str, client: anthropic.Anthropic | None = None) -> Theme:
    load_dotenv(ROOT / ".env")
    if client is None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            return default_theme()
        client = anthropic.Anthropic()
    reason = "sem resposta"
    for _ in range(2):  # uma tentativa e mais uma
        try:
            data = _parse(_ask(client, lines_text))
        except Exception as error:  # rede, cota ou JSON inválido: a pipeline segue com o tema padrão
            reason = type(error).__name__
            continue
        problems = _problems(data)
        if not problems:
            return Theme.from_dict(data)
        reason = "campos inválidos: " + ", ".join(problems)
    print(f"aviso: tema não gerado ({reason}); usando tema padrão", file=sys.stderr)
    return default_theme()


def _ask(client: anthropic.Anthropic, lines_text: str) -> str:
    message = client.messages.create(
        model=os.getenv("THEME_MODEL", MODEL_DEFAULT),
        max_tokens=600,
        system=SYSTEM,
        messages=[{"role": "user", "content": lines_text}],
    )
    # o modelo pode enviar bloco "thinking" antes do texto; junta só os blocos de texto
    return "".join(block.text for block in message.content if block.type == "text")


def _parse(text: str) -> object:
    return json.loads(FENCE.sub("", text.strip()))


def _problems(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["resposta não é um objeto JSON"]
    problems = []
    for key in ("title", "mood", "visual_concept"):
        if not isinstance(data.get(key), str):
            problems.append(key)
    keywords = data.get("keywords")
    if not (isinstance(keywords, list) and 3 <= len(keywords) <= 6 and all(isinstance(k, str) for k in keywords)):
        problems.append("keywords")
    palette = data.get("palette")
    if not (isinstance(palette, list) and 3 <= len(palette) <= 5 and all(isinstance(c, str) and HEX6.fullmatch(c) for c in palette)):
        problems.append("palette")
    font = data.get("font")
    if not isinstance(font, str) or font not in FONTS:
        problems.append("font")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera o tema com a Claude API e grava no song.json")
    parser.add_argument("--song", type=Path, required=True)
    args = parser.parse_args(argv)
    song = json.loads(args.song.read_text(encoding="utf-8"))
    song["theme"] = analyze_theme(flat_text(song["lines"])).to_dict()
    errors = validate_song(song)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    args.song.write_text(json.dumps(song, ensure_ascii=False, indent=2), encoding="utf-8")
    theme = song["theme"]
    print(f"tema: {theme['title']} | paleta {theme['palette']} | fonte {theme['font']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
