# Alinhamento forçado letra ↔ áudio com stable-ts, e CLI que mostra os tempos para conferência.
import argparse
import json
import os
import sys
from pathlib import Path

import stable_whisper
from dotenv import load_dotenv

from engine.audio import bpm, duration
from engine.lyrics import flat_text, parse_lyrics
from engine.postprocess import build_lines, split_by_counts
from engine.schema import Audio, Song, valid_song_file, validate_song
from engine.separate import separate_vocals, voice_dir


def align(audio: Path, lyrics_text: str, language: str = "pt",
          model_name: str = "small", separate: bool = True) -> Song:
    lyrics = parse_lyrics(lyrics_text)
    source = separate_vocals(audio, voice_dir(audio)) if separate else audio
    model = stable_whisper.load_model(model_name)  # GPU se houver; sem GPU, CPU
    result = model.align(str(source), flat_text(lyrics), language=language, original_split=True)
    total = duration(audio)
    audio_info = Audio(file=audio.name, duration=total, bpm=bpm(audio))
    return Song(language=language, audio=audio_info, lines=build_lines(lyrics, _groups(result, lyrics), total))


def is_cached(out_dir: Path, params: dict) -> bool:
    """O alinhamento de uma pasta só vale como cache com os mesmos modelo, idioma e separação de quando foi feito."""
    try:
        saved = json.loads((out_dir / "align.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return saved == params and valid_song_file(out_dir / "song.json")


def _timed(words) -> list[tuple[str, float, float]]:
    """Palavras do stable-ts viram tuplas com float puro (o stable-ts devolve numpy) e sem espaço no texto."""
    return [(w.word.strip(), float(w.start), float(w.end)) for w in words]


def _groups(result, lyrics: list[dict]) -> list[list[tuple[str, float, float]]]:
    """Agrupa as palavras por verso: pelos segmentos do alinhador, ou pela contagem se não baterem."""
    if len(result.segments) == len(lyrics):
        return [_timed(segment.words) for segment in result.segments]
    counts = [len(verse["text"].split()) for verse in lyrics]
    return split_by_counts(_timed(result.all_words()), counts)


def print_table(song: Song) -> None:
    print(f"{'id':>3}  {'início':>8}  {'fim':>8}  texto")
    for line in song.lines:
        print(f"{line.id:>3}  {line.start:>8.2f}  {line.end:>8.2f}  {line.text}")


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Alinha a letra ao áudio e grava o song.json")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--lyrics", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="caminho do song.json")
    parser.add_argument("--model", default=os.getenv("WHISPER_MODEL", "small"))
    parser.add_argument("--language", default="pt")
    parser.add_argument("--no-separate", action="store_true", help="não separar vocais com Demucs")
    args = parser.parse_args(argv)
    song = align(args.audio, args.lyrics.read_text(encoding="utf-8"),
                 args.language, args.model, not args.no_separate)
    errors = validate_song(song.to_dict())
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(song.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print_table(song)
    return 0


if __name__ == "__main__":
    sys.exit(main())
