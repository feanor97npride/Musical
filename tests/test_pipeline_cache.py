# Testes do slug e do cache da pipeline, com arquivos falsos e sem rodar modelos nem o render.
import argparse
import subprocess
from pathlib import Path

import pytest

from engine import pipeline


def make_job(tmp_path: Path, **flags: bool) -> pipeline.Job:
    audio = tmp_path / "Minha Música.mp3"
    audio.write_bytes(b"audio")
    args = argparse.Namespace(audio=audio, lyrics=tmp_path / "a.txt", style="karaoke", clip=None,
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


def test_render_pulado_quando_props_nao_mudou(tmp_path, monkeypatch):
    job = make_job(tmp_path)
    job.props.write_text("igual", encoding="utf-8")
    job.video.write_bytes(b"mp4")
    job.new_props = "igual"
    monkeypatch.setattr(pipeline.subprocess, "run", boom)
    assert pipeline._render(job) == "pulado (cache)"


def test_render_refeito_quando_estilo_muda(tmp_path, monkeypatch):
    job = make_job(tmp_path)
    job.props.write_text("antigo", encoding="utf-8")
    job.video.write_bytes(b"antigo")
    job.new_props = "novo"

    def fake_run(cmd, cwd, check):
        Path(cmd[-1]).write_bytes(b"novo")  # o último argumento é o caminho do vídeo temporário

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    assert pipeline._render(job) is None
    assert job.props.read_text(encoding="utf-8") == "novo"
    assert job.video.read_bytes() == b"novo"


def test_render_que_falha_mantem_os_arquivos_anteriores(tmp_path, monkeypatch):
    job = make_job(tmp_path)
    job.props.write_text("antigo", encoding="utf-8")
    job.video.write_bytes(b"antigo")
    job.new_props = "novo"

    def failing_run(cmd, cwd, check):
        Path(cmd[-1]).write_bytes(b"parcial")  # render morreu no meio
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(pipeline.subprocess, "run", failing_run)
    with pytest.raises(subprocess.CalledProcessError):
        pipeline._render(job)
    assert job.props.read_text(encoding="utf-8") == "antigo"
    assert job.video.read_bytes() == b"antigo"
    assert not (job.out / "video.tmp.mp4").exists()
