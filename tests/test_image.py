# Imagem de fundo enviada pelo usuário: corte para 9:16 e cache por imagem.
import json
import shutil
import subprocess

import pytest

from engine import image


def make_png(path, size="640x360"):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=red:s={size}",
                    "-frames:v", "1", str(path)], check=True)
    return path


def dims(path):
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    stream = json.loads(probe.stdout)["streams"][0]
    return stream["width"], stream["height"]


needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="precisa do ffmpeg")


@needs_ffmpeg
def test_corta_para_1080_por_1920(tmp_path):
    source = make_png(tmp_path / "foto.png")
    out = image.ensure_background(tmp_path, source, False)
    assert dims(out) == (1080, 1920)
    assert not (tmp_path / "background.tmp.jpg").exists()


@needs_ffmpeg
def test_reaproveita_o_corte_da_mesma_imagem(tmp_path, monkeypatch):
    source = make_png(tmp_path / "foto.png")
    first = image.ensure_background(tmp_path, source, False)
    monkeypatch.setattr(image, "crop_to", lambda src, dst, w, h: pytest.fail("não devia cortar de novo"))
    assert image.ensure_background(tmp_path, source, False) == first


@needs_ffmpeg
def test_imagem_nova_refaz_o_corte(tmp_path):
    source = make_png(tmp_path / "foto.png")
    image.ensure_background(tmp_path, source, False)
    make_png(source, size="800x800")  # outra imagem no mesmo caminho: o hash muda
    image.ensure_background(tmp_path, source, False)
    assert dims(tmp_path / "background.jpg") == (1080, 1920)


def test_sem_arquivo_avisa_claramente(tmp_path):
    with pytest.raises(RuntimeError, match="--background-image"):
        image.ensure_background(tmp_path, None, False)
    with pytest.raises(RuntimeError, match="--background-image"):
        image.ensure_background(tmp_path, tmp_path / "nao-existe.jpg", False)


@needs_ffmpeg
def test_formato_horizontal_corta_para_16_por_9_e_tem_arquivo_proprio(tmp_path):
    source = make_png(tmp_path / "foto.png")
    vertical = image.ensure_background(tmp_path, source, False)
    horizontal = image.ensure_background(tmp_path, source, False, "horizontal")
    assert horizontal.name == "background-16x9.jpg" and vertical.name == "background.jpg"
    assert dims(horizontal) == (1920, 1080)
    assert dims(vertical) == (1080, 1920)
