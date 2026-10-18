# Lote: gera o vídeo de cada par <nome>.mp3 + <nome>.txt de uma pasta, uma música por vez.
import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from engine import pipeline


def pairs(folder: Path) -> list[tuple[Path, Path]]:
    """Pares MP3 + letra da pasta, em ordem alfabética. MP3 sem letra é ignorado."""
    found = []
    for audio in sorted(folder.glob("*.mp3")):
        lyrics = audio.with_suffix(".txt")
        if lyrics.exists():
            found.append((audio, lyrics))
    return found


def run_batch(folder: Path, options: argparse.Namespace) -> list[tuple[str, int, float]]:
    results = []
    for audio, lyrics in pairs(folder):
        print(f"== {audio.name} ==", flush=True)
        began = time.monotonic()
        try:
            code = pipeline.run(argparse.Namespace(**{**vars(options), "audio": audio, "lyrics": lyrics}))
        except Exception as error:  # um erro numa música não para as outras
            print(f"erro: {error}", file=sys.stderr)
            code = 1
        results.append((audio.name, code, time.monotonic() - began))
    return results


def main(argv: list[str] | None = None) -> int:
    load_dotenv(pipeline.ROOT / ".env")
    parser = argparse.ArgumentParser(description="Gera os vídeos de todas as músicas de uma pasta",
                                     parents=[pipeline.build_options()])
    parser.add_argument("--folder", type=Path, required=True, help="pasta com pares <nome>.mp3 e <nome>.txt")
    args = parser.parse_args(argv)
    pipeline.check_options(parser, args)
    if not pairs(args.folder):
        print(f"nenhum par MP3 + TXT encontrado em {args.folder}", file=sys.stderr)
        return 1
    results = run_batch(args.folder, args)
    print("\nresumo:")
    for name, code, seconds in results:
        print(f"  {name}: {'ok' if code == 0 else 'erro'} ({seconds:.0f} s)")
    return 0 if all(code == 0 for _, code, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
