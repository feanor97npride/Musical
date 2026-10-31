# Testes do vídeo enviado: o áudio sai como MP3, a checagem de som funciona e o corte tem o tamanho certo.
import subprocess
from pathlib import Path

import pytest

from engine import image
from web import video_in

pytestmark = pytest.mark.skipif(video_in.shutil.which("ffmpeg") is None, reason="precisa do ffmpeg")


def video(path: Path, com_som: bool = True, largura: int = 640, altura: int = 360) -> Path:
    comando = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=red:s={largura}x{altura}:d=2"]
    if com_som:
        comando += ["-f", "lavfi", "-i", "sine=frequency=440:duration=2"]
    comando += ["-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(comando, check=True)
    return path


def tamanho(path: Path) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0:s=x", str(path)], capture_output=True, text=True, check=True)
    largura, altura = out.stdout.strip().split("x")
    return int(largura), int(altura)


def test_checa_faixa_de_som(tmp_path):
    assert video_in.has_audio(video(tmp_path / "com.mp4", com_som=True))
    assert not video_in.has_audio(video(tmp_path / "sem.mp4", com_som=False))


def test_extrai_o_som_como_mp3(tmp_path):
    mp3 = tmp_path / "musica.mp3"
    video_in.extract_audio(video(tmp_path / "v.mp4"), mp3)
    assert mp3.stat().st_size > 0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=format_name", "-of", "csv=p=0", str(mp3)],
                         capture_output=True, text=True, check=True)
    assert "mp3" in out.stdout


def test_corte_vertical_e_horizontal_tem_o_tamanho_certo(tmp_path):
    origem = video(tmp_path / "v.mp4", largura=640, altura=360)
    vertical = tmp_path / "vertical.mp4"
    horizontal = tmp_path / "horizontal.mp4"
    image.crop_video(origem, vertical, 1080, 1920)
    image.crop_video(origem, horizontal, 1920, 1080)
    assert tamanho(vertical) == (1080, 1920)
    assert tamanho(horizontal) == (1920, 1080)
