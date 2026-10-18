# CLI de ponta a ponta: MP3 + letra → output/<slug>/video-<variante>.mp4, com cache por etapa.
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from engine import align, separate, theme
from engine.cuts import plan_cuts
from engine.lyrics import flat_text
from engine.names import make_slug, variant_name
from engine.props import build_props, parse_clip
from engine.schema import validate_song

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
RENDERER = ROOT / "renderer"
TOTAL_STEPS = 5


@dataclass
class Job:
    args: argparse.Namespace
    lyrics: str
    out: Path
    new_props: str = ""  # props da rodada atual; só vira props-<variante>.json depois que o render termina

    @property
    def song(self) -> Path:
        return self.out / "song.json"

    @property
    def variant(self) -> str:
        return variant_name(self.args.style, self.args.background, self.args.clip)

    @property
    def props(self) -> Path:
        return self.out / f"props-{self.variant}.json"

    @property
    def video(self) -> Path:
        return self.out / f"video-{self.variant}.mp4"


class StepError(Exception):
    def __init__(self, label: str, cause: Exception) -> None:
        super().__init__(f"etapa '{label}' falhou: {cause}")
        self.label = label
        self.cause = cause


def _write_song(path: Path, song: dict) -> None:
    errors = validate_song(song)
    if errors:
        raise ValueError("song.json inválido: " + "; ".join(errors))
    path.write_text(json.dumps(song, ensure_ascii=False, indent=2), encoding="utf-8")


def _separate(job: Job) -> str | None:
    if job.args.no_separate:
        return "desligado (--no-separate)"
    if (job.out / "vocals.wav").exists() and not job.args.force:
        return "pulado (cache)"
    separate.separate_vocals(job.args.audio, job.out, force=job.args.force)
    return None


def _align(job: Job) -> str | None:
    if job.song.exists() and not job.args.force:
        return "pulado (cache)"
    song = align.align(job.args.audio, job.lyrics, job.out, job.args.language,
                       job.args.model, not job.args.no_separate)
    _write_song(job.song, song.to_dict())
    return None


def _theme(job: Job) -> str | None:
    if job.args.skip_theme:
        return "desligado (--skip-theme)"
    song = json.loads(job.song.read_text(encoding="utf-8"))
    # o tema padrão é o que sobra quando a API falha; nesse caso tenta de novo
    if song.get("theme") not in (None, theme.default_theme().to_dict()) and not job.args.force:
        return "pulado (cache)"
    song["theme"] = theme.analyze_theme(flat_text(song["lines"])).to_dict()
    _write_song(job.song, song)
    return None


def _props(job: Job) -> str | None:
    props = build_props(job.song, job.args.audio, job.args.style, job.args.background, job.args.clip)
    job.new_props = json.dumps(props, ensure_ascii=False, indent=2)
    return None


def _cut_jobs(job: Job) -> list[Job]:
    """Um job por corte: mesmo estilo e fundo, cada um com o clip do seu trecho."""
    song = json.loads(job.song.read_text(encoding="utf-8"))
    return [Job(argparse.Namespace(**{**vars(job.args), "clip": clip}), job.lyrics, job.out)
            for clip in plan_cuts(song, job.args.cuts)]


def _props_all(jobs: list[Job]) -> str | None:
    for item in jobs:
        _props(item)
    return None


def _render(job: Job) -> str | None:
    unchanged = job.props.exists() and job.props.read_text(encoding="utf-8") == job.new_props
    if unchanged and job.video.exists() and not job.args.force:
        return "pulado (cache)"
    tmp_props = job.out / "props.tmp.json"
    tmp_video = job.out / "video.tmp.mp4"
    tmp_props.write_text(job.new_props, encoding="utf-8")
    try:
        npm = shutil.which("npm")  # no Windows é npm.CMD; sem o caminho completo o Windows não acha
        if npm is None:
            raise RuntimeError("npm não encontrado: instale o Node.js 18 ou superior")
        subprocess.run([npm, "run", "render", "--", str(tmp_props), str(tmp_video)], cwd=RENDERER, check=True)
        os.replace(tmp_video, job.video)  # vídeo antes do props: se cair no meio, a próxima rodada refaz
        os.replace(tmp_props, job.props)
    finally:
        tmp_video.unlink(missing_ok=True)
        tmp_props.unlink(missing_ok=True)
    return None


def _step(number: int, label: str, action: Callable[[], str | None]) -> None:
    print(f"[{number}/{TOTAL_STEPS}] {label}... ", end="", flush=True)
    began = time.monotonic()
    try:
        note = action()
    except Exception as error:
        print("falhou")
        raise StepError(label, error) from error
    print(note or f"ok ({time.monotonic() - began:.0f} s)")


def run(args: argparse.Namespace) -> int:
    began = time.monotonic()
    lyrics = args.lyrics.read_text(encoding="utf-8")
    job = Job(args, lyrics, OUTPUT / make_slug(args.audio, lyrics))
    job.out.mkdir(parents=True, exist_ok=True)
    print(f"pasta: {job.out}")
    try:
        _step(1, "Separando vocais", lambda: _separate(job))
        _step(2, "Alinhando letra", lambda: _align(job))
        _step(3, "Gerando tema", lambda: _theme(job))
        jobs = _cut_jobs(job) if args.cuts else [job]  # o song.json já existe aqui: o alinhamento acabou
        _step(4, "Montando props", lambda: _props_all(jobs))
        for number, item in enumerate(jobs, 1):
            label = "Renderizando vídeo" if len(jobs) == 1 else f"Renderizando corte {number} de {len(jobs)}"
            _step(5, label, lambda item=item: _render(item))
    except StepError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 1
    for item in jobs:
        print(f"vídeo: {item.video}")
    print(f"tempo total: {time.monotonic() - began:.0f} s")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Gera o vídeo a partir de MP3 + letra")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--lyrics", type=Path, required=True)
    parser.add_argument("--style", default="karaoke", help="highlight, oneword ou karaoke")
    parser.add_argument("--background", default="gradient", help="gradient (animado), solid ou aurora")
    parser.add_argument("--clip", type=parse_clip, default=None, help="início:fim em segundos, ex.: 30:75")
    parser.add_argument("--cuts", type=float, default=None, help="um vídeo por corte de cerca de N segundos, ex.: 30")
    parser.add_argument("--no-separate", action="store_true", help="não separar vocais com Demucs")
    parser.add_argument("--skip-theme", action="store_true", help="não chamar a Claude API")
    parser.add_argument("--force", action="store_true", help="refazer todas as etapas")
    parser.add_argument("--model", default=os.getenv("WHISPER_MODEL", "small"))
    parser.add_argument("--language", default="pt")
    args = parser.parse_args(argv)
    if args.cuts is not None and args.cuts <= 0:
        parser.error("--cuts precisa ser maior que zero")
    if args.cuts is not None and args.clip is not None:
        parser.error("use --clip ou --cuts, não os dois")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
