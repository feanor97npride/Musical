# Lote: gera o vídeo de cada par <nome>.mp3 + <nome>.txt de uma pasta, uma música por vez.
import argparse
import sys
import time
from itertools import product
from pathlib import Path

from dotenv import load_dotenv

from engine import pipeline
from engine.names import variant_name
from engine.props import BACKGROUNDS, SUBTITLE_STYLES

VARIANT_CHOICES = {"background": BACKGROUNDS, "style": SUBTITLE_STYLES}


def pairs(folder: Path) -> list[tuple[Path, Path]]:
    """Pares MP3 + letra da pasta, em ordem alfabética. MP3 sem letra é ignorado."""
    found = []
    for audio in sorted(folder.glob("*.mp3")):
        lyrics = audio.with_suffix(".txt")
        if lyrics.exists():
            found.append((audio, lyrics))
    return found


def parse_variants(text: str) -> list[dict[str, str]]:
    """'background=gradient,aurora;style=karaoke' -> uma combinação para cada par de valores."""
    axes: dict[str, list[str]] = {}
    for part in text.split(";"):
        key, _, raw = part.partition("=")
        key = key.strip()
        values = [value.strip() for value in raw.split(",") if value.strip()]
        if key not in VARIANT_CHOICES or key in axes:
            raise argparse.ArgumentTypeError(f"chave inválida ou repetida: '{key}' (use background ou style)")
        if not values:
            raise argparse.ArgumentTypeError(f"nenhum valor para '{key}'")
        bad = [value for value in values if value not in VARIANT_CHOICES[key]]
        if bad:
            raise argparse.ArgumentTypeError(f"valor inválido para '{key}': {', '.join(bad)} "
                                             f"(opções: {', '.join(sorted(VARIANT_CHOICES[key]))})")
        axes[key] = values
    return [dict(zip(axes, combo)) for combo in product(*axes.values())]


def run_batch(folder: Path, options: argparse.Namespace,
              variants: list[dict[str, str]] | None = None) -> list[tuple[str, int, float]]:
    results = []
    for audio, lyrics in pairs(folder):
        for variant in variants or [{}]:
            args = argparse.Namespace(**{**vars(options), **variant, "audio": audio, "lyrics": lyrics})
            name = f"{audio.name} {variant_name(args.style, args.background, args.clip)}" if variant else audio.name
            print(f"== {name} ==", flush=True)
            began = time.monotonic()
            try:
                code = pipeline.run(args)
            except Exception as error:  # um erro numa música não para as outras
                print(f"erro: {error}", file=sys.stderr)
                code = 1
            results.append((name, code, time.monotonic() - began))
    return results


def main(argv: list[str] | None = None) -> int:
    load_dotenv(pipeline.ROOT / ".env")
    parser = argparse.ArgumentParser(description="Gera os vídeos de todas as músicas de uma pasta",
                                     parents=[pipeline.build_options()])
    parser.add_argument("--folder", type=Path, required=True, help="pasta com pares <nome>.mp3 e <nome>.txt")
    parser.add_argument("--variants", type=parse_variants, default=None,
                        help="um vídeo por combinação, ex.: background=gradient,aurora;style=karaoke,oneword")
    args = parser.parse_args(argv)
    pipeline.check_options(parser, args)
    if not pairs(args.folder):
        print(f"nenhum par MP3 + TXT encontrado em {args.folder}", file=sys.stderr)
        return 1
    results = run_batch(args.folder, args, args.variants)
    print("\nresumo:")
    for name, code, seconds in results:
        print(f"  {name}: {'ok' if code == 0 else 'erro'} ({seconds:.0f} s)")
    return 0 if all(code == 0 for _, code, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
