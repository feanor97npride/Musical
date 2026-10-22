# Testes do slug e do cache da pipeline, com arquivos falsos e sem rodar modelos nem o render.
import argparse
import json
import subprocess
from pathlib import Path

import pytest

from engine import pipeline, render


def make_job(tmp_path: Path, **flags: bool) -> pipeline.Job:
    audio = tmp_path / "Minha Música.mp3"
    audio.write_bytes(b"audio")
    args = argparse.Namespace(audio=audio, lyrics=tmp_path / "a.txt", style="karaoke", background="gradient", clip=None, format="vertical",
                              no_separate=False, skip_theme=False, force=False, model="small", language="pt")
    for name, value in flags.items():
        setattr(args, name, value)
    out = tmp_path / "out"
    out.mkdir()
    return pipeline.Job(args, "um\ndois", out)


def boom(*_args, **_kwargs):
    raise AssertionError("não devia rodar")


def test_slug_tem_nome_limpo_e_muda_com_a_letra(tmp_path):
    audio = tmp_path / "Minha Música.mp3"
    audio.write_bytes(b"audio")
    slug = pipeline.make_slug(audio, "um")
    assert slug.startswith("minha-musica-")
    assert len(slug.rsplit("-", 1)[1]) == 8
    assert pipeline.make_slug(audio, "dois") != slug


def test_separacao_pulada_quando_vocals_existe(tmp_path, monkeypatch):
    job = make_job(tmp_path)
    (job.out / "vocals.wav").write_bytes(b"wav")
    monkeypatch.setattr(pipeline.separate, "separate_vocals", boom)
    assert pipeline._separate(job) == "pulado (cache)"


def test_alinhamento_pulado_quando_song_existe(tmp_path, monkeypatch):
    job = make_job(tmp_path)
    job.song.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(pipeline.align, "align", boom)
    assert pipeline._align(job) == "pulado (cache)"


def node_falso(conteudo: bytes, falha: bool = False):
    """Faz o que o render-batch.mjs faz: grava o vídeo temporário e troca os arquivos finais (ou morre no meio)."""
    def run(cmd, cwd, check):
        for entry in json.loads(Path(cmd[-1]).read_text(encoding="utf-8")):
            Path(entry["video"]).write_bytes(conteudo)
            if falha:
                raise subprocess.CalledProcessError(1, cmd)
            Path(entry["video"]).replace(entry["finalVideo"])
            Path(entry["props"]).replace(entry["finalProps"])
    return run


def test_render_pulado_quando_props_nao_mudou(tmp_path, monkeypatch):
    job = make_job(tmp_path)
    job.props.write_text("igual", encoding="utf-8")
    job.video.write_bytes(b"mp4")
    job.new_props = "igual"
    monkeypatch.setattr(render.subprocess, "run", boom)
    assert render.render_all([job]) == "pulado (cache)"


def test_render_refeito_quando_estilo_muda(tmp_path, monkeypatch):
    job = make_job(tmp_path)
    job.props.write_text("antigo", encoding="utf-8")
    job.video.write_bytes(b"antigo")
    job.new_props = "novo"
    monkeypatch.setattr(render.subprocess, "run", node_falso(b"novo"))
    assert render.render_all([job]) is None
    assert job.props.read_text(encoding="utf-8") == "novo"
    assert job.video.read_bytes() == b"novo"


def test_render_que_falha_mantem_os_arquivos_anteriores(tmp_path, monkeypatch):
    job = make_job(tmp_path)
    job.props.write_text("antigo", encoding="utf-8")
    job.video.write_bytes(b"antigo")
    job.new_props = "novo"
    monkeypatch.setattr(render.subprocess, "run", node_falso(b"parcial", falha=True))  # render morreu no meio
    with pytest.raises(subprocess.CalledProcessError):
        render.render_all([job])
    assert job.props.read_text(encoding="utf-8") == "antigo"
    assert job.video.read_bytes() == b"antigo"
    assert not job.video.with_suffix(".tmp.mp4").exists()


def test_props_usa_o_fundo_escolhido(tmp_path, monkeypatch):
    job = make_job(tmp_path, background="solid")
    monkeypatch.setattr(pipeline, "build_props", lambda *args, **kwargs: {"fundo": args[3]})  # args[3] é o fundo
    pipeline._props(job)
    assert json.loads(job.new_props) == {"fundo": "solid"}


def test_cada_variante_tem_seu_video(tmp_path):
    job = make_job(tmp_path)
    assert job.video.name == "video-karaoke-gradient.mp4"
    job.args.background = "solid"
    assert job.video.name == "video-karaoke-solid.mp4"
    job.args.clip = (0.0, 30.0)
    assert job.video.name == "video-karaoke-solid-0-30.mp4"
    assert job.props.name == "props-karaoke-solid-0-30.json"


def test_trechos_quase_iguais_tem_arquivos_diferentes(tmp_path):
    job = make_job(tmp_path)
    job.args.clip = (30.0, 75.0)
    first = job.video
    job.args.clip = (30.00001, 75.0)
    assert job.video != first


def test_fundo_imagem_prepara_o_arquivo_enviado_e_passa_o_caminho(tmp_path, monkeypatch):
    job = make_job(tmp_path, background="image", background_image=tmp_path / "foto.jpg")
    job.args.background_image.write_bytes(b"jpg")
    job.song.write_text(json.dumps({"theme": None}), encoding="utf-8")
    monkeypatch.setattr(pipeline.image, "crop_to", lambda src, dst, w, h: dst.write_bytes(b"corte"))
    seen = {}
    monkeypatch.setattr(pipeline, "build_props", lambda *args, **kwargs: seen.update(kwargs) or {"ok": True})
    pipeline._props(job)
    assert seen["background_image"] == job.out / "background.jpg"
