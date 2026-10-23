# Transcrição da letra pelo áudio (Whisper via stable-ts), sobre a voz separada: gera o texto para o usuário revisar.
import argparse
import os
import sys
from pathlib import Path

import stable_whisper
from dotenv import load_dotenv

from engine.separate import separate_vocals, voice_dir


def words(vocals: Path, language: str = "pt", model_name: str = "small") -> list[tuple[str, float, float]]:
    model = stable_whisper.load_model(model_name)  # GPU se houver; sem GPU, CPU
    result = model.transcribe(str(vocals), language=language)
    return [(word.word.strip(), float(word.start), float(word.end)) for word in result.all_words()]


def group_lines(timed: list[tuple[str, float, float]], pause: float = 1.0, max_words: int = 8) -> list[str]:
    """Um verso por linha: quebra depois de uma pausa longa ou de max_words palavras."""  # shortcut: 1 s e 8 palavras, ajustar ouvindo a música
    lines: list[str] = []
    current: list[str] = []
    previous_end = 0.0
    for text, start, end in timed:
        if not text:
            continue
        if current and (start - previous_end > pause or len(current) >= max_words):
            lines.append(" ".join(current))
            current = []
        current.append(text)
        previous_end = end
    if current:
        lines.append(" ".join(current))
    return lines


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Gera o texto da letra a partir do áudio, para revisar antes do vídeo")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="arquivo .txt com a letra gerada")
    parser.add_argument("--model", default=os.getenv("WHISPER_MODEL", "small"))
    parser.add_argument("--language", default="pt")
    parser.add_argument("--force", action="store_true", help="sobrescreve o .txt se ele já existir")
    args = parser.parse_args(argv)
    if args.out.exists() and not args.force:
        print(f"{args.out} já existe: use --force para sobrescrever", file=sys.stderr)
        return 1
    vocals = separate_vocals(args.audio, voice_dir(args.audio), force=args.force)  # voz no cache por áudio, como o alinhamento
    lines = group_lines(words(vocals, args.language, args.model))
    if not lines:  # áudio sem fala reconhecível: não grava um arquivo vazio que pareceria uma letra
        print("nenhuma palavra reconhecida: a letra não foi gravada", file=sys.stderr)
        return 1
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"letra gerada: {len(lines)} versos em {args.out}. Revise antes de gerar o vídeo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
