# CLI de ponta a ponta: MP3 + letra → output/<slug>/video-<variante>.mp4, com cache por etapa.
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from engine import align, image, separate, theme
from engine.audio import beats
from engine.cuts import plan_cuts
from engine.export import export_all
from engine.lyrics import flat_text
from engine.names import make_slug, variant_name
from engine.props import build_props, parse_clip
from engine.schema import write_song
from engine.steps import StepError, run_step

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
RENDERER = ROOT / "renderer"


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
        return variant_name(self.args.style, self.args.background, self.args.clip, self.args.format)

    @property
    def props(self) -> Path:
        return self.out / f"props-{self.variant}.json"

    @property
    def video(self) -> Path:
        return self.out / f"video-{self.variant}.mp4"


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
    write_song(job.song, song.to_dict())
    return None


def _beats(job: Job) -> str | None:
    song = json.loads(job.song.read_text(encoding="utf-8"))
    if song["audio"].get("beats") is not None and not job.args.force:
        return "pulado (cache)"
    song["audio"]["beats"] = beats(job.args.audio)
    write_song(job.song, song)
    return None


def _theme(job: Job) -> str | None:
    if job.args.skip_theme:
        return "desligado (--skip-theme)"
    song = json.loads(job.song.read_text(encoding="utf-8"))
    # o tema padrão é o que sobra quando a API falha; nesse caso tenta de novo
    if song.get("theme") not in (None, theme.default_theme().to_dict()) and not job.args.force:
        return "pulado (cache)"
    song["theme"] = theme.analyze_theme(flat_text(song["lines"])).to_dict()
    write_song(job.song, song)
    return None


def _props(job: Job) -> str | None:
    background = image.ensure_background(job.out, job.args.background_image, job.args.force, job.args.format) if job.args.background == "image" else None
    props = build_props(job.song, job.args.audio, job.args.style, job.args.background, job.args.clip, background_image=background, fmt=job.args.format)
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


def run(args: argparse.Namespace) -> int:
    began = time.monotonic()
    lyrics = args.lyrics.read_text(encoding="utf-8")
    job = Job(args, lyrics, OUTPUT / make_slug(args.audio, lyrics))
    job.out.mkdir(parents=True, exist_ok=True)
    print(f"pasta: {job.out}")
    try:
        run_step(1, "Separando vocais", lambda: _separate(job))
        run_step(2, "Alinhando letra", lambda: _align(job))
        run_step(3, "Achando batidas", lambda: _beats(job))
        run_step(4, "Gerando tema", lambda: _theme(job))
        jobs = _cut_jobs(job) if args.cuts else [job]  # o song.json já existe aqui: o alinhamento acabou
        run_step(5, "Preparando imagem e montando props" if args.background == "image" else "Montando props", lambda: _props_all(jobs))
        for number, item in enumerate(jobs, 1):
            label = "Renderizando vídeo" if len(jobs) == 1 else f"Renderizando corte {number} de {len(jobs)}"
            run_step(6, label, lambda item=item: _render(item))
        for item in jobs:
            print(f"vídeo: {item.video}")  # antes da exportação: um erro nela não esconde onde está o vídeo
        run_step(7, "Exportando para postar", lambda: export_all(args, [(item.video, item.variant) for item in jobs]))
    except StepError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 1
    print(f"tempo total: {time.monotonic() - began:.0f} s")
    return 0


def build_options() -> argparse.ArgumentParser:
    """Opções que valem para cada música (sem o áudio e a letra). O lote reaproveita esta lista."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--style", default="karaoke", help="highlight, oneword ou karaoke")
    parser.add_argument("--background", default="gradient", help="gradient (animado), solid, aurora, aurora-gl, sunrise ou image (imagem enviada)")
    parser.add_argument("--background-image", type=Path, default=None, help="imagem JPG ou PNG para o fundo image (cortada no centro)")
    parser.add_argument("--format", default="vertical", choices=["vertical", "horizontal"], help="vertical 9:16 (Shorts, TikTok) ou horizontal 16:9 (YouTube)")
    parser.add_argument("--clip", type=parse_clip, default=None, help="início:fim em segundos, ex.: 30:75")
    parser.add_argument("--cuts", type=float, default=None, help="um vídeo por corte de cerca de N segundos, ex.: 30")
    parser.add_argument("--export", action="store_true", help="também gera uma cópia pronta para postar em para-postar/")
    parser.add_argument("--no-separate", action="store_true", help="não separar vocais com Demucs")
    parser.add_argument("--skip-theme", action="store_true", help="não chamar a Claude API")
    parser.add_argument("--force", action="store_true", help="refazer todas as etapas")
    parser.add_argument("--model", default=os.getenv("WHISPER_MODEL", "small"))
    parser.add_argument("--language", default="pt")
    return parser


def check_options(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.cuts is not None and args.cuts <= 0:
        parser.error("--cuts precisa ser maior que zero")
    if args.cuts is not None and args.clip is not None:
        parser.error("use --clip ou --cuts, não os dois")
    if args.export and shutil.which("ffmpeg") is None: parser.error("--export precisa do ffmpeg no PATH")


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Gera o vídeo a partir de MP3 + letra", parents=[build_options()])
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--lyrics", type=Path, required=True)
    args = parser.parse_args(argv)
    check_options(parser, args)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
