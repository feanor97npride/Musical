# Fundo com imagem gerada por IA (Gemini): o tema da letra vira um prompt e a imagem sai em 1080x1920 para o vídeo.
import base64
import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import httpx

DEFAULT_MODEL = "gemini-2.5-flash-image"  # shortcut: nome não confirmado na doc oficial; trocar com IMAGE_MODEL no .env
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RULES = "vertical, sem texto, sem letras, sem logotipos, sem nomes de artistas"


class ImageError(Exception):
    pass


def build_prompt(theme: dict | None, description: str) -> str:
    parts = [description.strip()] if description.strip() else []
    if theme:
        parts += [theme.get("visual_concept", ""), theme.get("mood", ""), ", ".join(theme.get("keywords", []))]
    return "Imagem de fundo para um vídeo vertical: " + "; ".join(p for p in parts if p) + f". Estilo: {RULES}."


def generate_image(prompt: str, api_key: str, post: Callable[..., httpx.Response] = httpx.post) -> bytes:
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}
    model = os.getenv("IMAGE_MODEL", DEFAULT_MODEL)
    response = post(API_URL.format(model=model), json=body, headers={"x-goog-api-key": api_key}, timeout=120)
    if response.status_code != 200:
        raise ImageError(f"a API de imagem respondeu {response.status_code}")  # sem o corpo: pode repetir dados da conta
    try:
        parts = response.json()["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise ImageError("a API de imagem não devolveu imagem") from error
    images = [part["inlineData"]["data"] for part in parts if "inlineData" in part and not part.get("thought")]
    if not images:
        raise ImageError("a API de imagem não devolveu imagem (pode ter recusado o pedido)")
    return base64.b64decode(images[-1])


def save_background(raw: bytes, out: Path) -> None:
    """Corta para 1080x1920 (proporção 9:16) e grava em JPEG."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg não encontrado no PATH")
    source = out.with_suffix(".raw")
    source.write_bytes(raw)
    try:
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(source), "-vf",
                        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                        "-frames:v", "1", str(out)], check=True)
    finally:
        source.unlink(missing_ok=True)


def ensure_background(out: Path, song: dict, description: str, force: bool) -> Path:
    """Gera a imagem da música (uma por pasta) e devolve o caminho; reaproveita a que já existe com o mesmo prompt."""
    target = out / "background.jpg"
    prompt_file = out / "background.prompt.txt"
    prompt = build_prompt(song.get("theme"), description)
    if target.exists() and prompt_file.exists() and prompt_file.read_text(encoding="utf-8") == prompt and not force:
        return target
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("falta GEMINI_API_KEY no .env para gerar a imagem de fundo")
    raw = generate_image(prompt, api_key)
    tmp = out / "background.tmp.jpg"
    save_background(raw, tmp)
    os.replace(tmp, target)  # só troca a imagem depois que o corte terminou, como o vídeo
    prompt_file.write_text(prompt, encoding="utf-8")
    return target
