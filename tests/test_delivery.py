# Testes da entrega para a pasta de saída do Drive: os MP4 prontos e o postar.txt vão para uma subpasta por música.
from pathlib import Path

import pytest

from engine.export import exported_path, part_name
from web import delivery
from web.jobs import Job, JobQueue


def job_pronto(tmp_path: Path, library_name: str | None = "Musica A") -> Job:
    folder = tmp_path / "output" / "slug"
    folder.mkdir(parents=True)
    audio = tmp_path / "job" / "musica-a.mp3"
    video = folder / "video-karaoke-gradient.mp4"
    video.write_bytes(b"mp4")
    copia = exported_path(video, audio)  # a cópia para postar que a pipeline com --export grava
    copia.parent.mkdir(exist_ok=True)
    copia.write_bytes(b"copia")
    return Job("id", folder, audio, "karaoke", "gradient", None, video=video, ready_videos=[video],
               library_name=library_name)


def test_entrega_copia_o_video_e_o_postar_txt(tmp_path):
    job = job_pronto(tmp_path)
    dest = delivery.deliver(job, tmp_path / "saida")
    assert dest == tmp_path / "saida" / "Musica A"
    assert (dest / part_name(job.audio, 1, 1)).read_bytes() == b"copia"
    assert (dest / "postar.txt").exists()


def test_sem_pasta_de_saida_nao_cria_nada(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIVE_OUTPUT_DIR", str(tmp_path / "saida"))
    delivery.deliver_ready(job_pronto(tmp_path, library_name=None))  # envio pelo formulário não vai para o Drive
    assert not (tmp_path / "saida").exists()


def test_com_pasta_de_saida_entrega_a_musica_da_biblioteca(tmp_path, monkeypatch):
    (tmp_path / "saida").mkdir()  # a pasta de saída do Drive tem que existir (sincronizada)
    monkeypatch.setenv("DRIVE_OUTPUT_DIR", str(tmp_path / "saida"))
    delivery.deliver_ready(job_pronto(tmp_path))
    assert (tmp_path / "saida" / "Musica A" / "postar.txt").exists()


def test_pasta_de_saida_ausente_levanta_erro_e_nao_cria_pastas(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIVE_OUTPUT_DIR", str(tmp_path / "sumiu"))
    with pytest.raises(OSError):
        delivery.deliver_ready(job_pronto(tmp_path))
    assert not (tmp_path / "sumiu").exists()


def test_falha_na_copia_nao_derruba_a_fila(tmp_path, caplog):
    queue = JobQueue()

    def sem_disco(job):
        raise OSError("pasta do Drive fora do ar")

    queue.on_ready = sem_disco
    queue._deliver(job_pronto(tmp_path))  # não pode levantar: o job continua pronto no PC
    assert "pasta do Drive" in caplog.text
