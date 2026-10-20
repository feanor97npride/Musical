# build_props(): monta o props.json do Remotion e copia o áudio para renderer/public/audio/.
import argparse
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

from engine.schema import validate_song

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_AUDIO = ROOT / "renderer" / "public" / "audio"
PUBLIC_BG = ROOT / "renderer" / "public" / "bg"
SUBTITLE_STYLES = {"highlight", "oneword", "karaoke"}
BACKGROUNDS = {"solid", "gradient", "aurora", "aurora-gl", "sunrise", "image"}


def build_props(song_path: Path, audio_path: Path, subtitle: str = "highlight", background: str = "gradient",
                clip: tuple[float, float] | None = None, public_audio: Path = PUBLIC_AUDIO,
                background_image: Path | None = None, public_bg: Path = PUBLIC_BG) -> dict:
    song = json.loads(song_path.read_text(encoding="utf-8"))
    errors = validate_song(song)
    if errors:
        raise ValueError("song.json inválido: " + "; ".join(errors))
    if subtitle not in SUBTITLE_STYLES:
        raise ValueError(f"estilo de legenda desconhecido: {subtitle}")
    if background not in BACKGROUNDS:
        raise ValueError(f"fundo desconhecido: {background}")
    if background == "image" and (background_image is None or not background_image.exists()):
        raise ValueError("fundo de imagem sem o arquivo da imagem gerada")
    if clip is not None and not 0 <= clip[0] < clip[1] <= song["audio"]["duration"]:
        raise ValueError("clip fora da duração da música")
    name = _audio_name(audio_path, song)
    public_audio.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(audio_path, public_audio / name)
    props = {
        "song": song,
        "audioFile": f"audio/{name}",
        "style": {"subtitle": subtitle, "background": background},
        "clip": {"start": clip[0], "end": clip[1]} if clip else None,
    }
    if background == "image":
        # a pasta da música (output/<slug>) dá um nome único à imagem no renderer
        bg_name = f"{background_image.parent.name}.jpg"
        public_bg.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(background_image, public_bg / bg_name)
        props["backgroundFile"] = f"bg/{bg_name}"
    return props


def _audio_name(audio_path: Path, song: dict) -> str:
    stem = unicodedata.normalize("NFKD", audio_path.stem).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "musica"
    lyrics = "\n".join(line["text"] for line in song["lines"])
    digest = hashlib.sha1(audio_path.read_bytes() + lyrics.encode("utf-8")).hexdigest()[:8]
    return f"{stem}-{digest}{audio_path.suffix.lower()}"


def parse_clip(text: str) -> tuple[float, float]:
    start, end = text.split(":")
    return float(start), float(end)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Monta o props.json do Remotion")
    parser.add_argument("--song", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--style", default="highlight", help="highlight, oneword ou karaoke")
    parser.add_argument("--background", default="gradient", help="gradient, solid, aurora, aurora-gl ou sunrise")
    parser.add_argument("--clip", type=parse_clip, default=None, help="início:fim em segundos, ex.: 30:75")
    parser.add_argument("--out", type=Path, required=True, help="caminho do props.json")
    args = parser.parse_args(argv)
    try:
        props = build_props(args.song, args.audio, args.style, args.background, args.clip)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"props gravado em {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
