# Testes da web mínima: recusas de envio e o fluxo do job, com a pipeline trocada por um fake.
import time

import pytest
from fastapi.testclient import TestClient

from engine import pipeline
from web import app as web_app
from web import jobs

MP3 = ("musica.mp3", b"ID3fake", "audio/mpeg")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "UPLOADS", tmp_path / "uploads")
    monkeypatch.setattr(jobs, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "")  # um .env com senha não pode mudar os testes
    with TestClient(web_app.app) as test_client:
        yield test_client


def send(client, audio=MP3, lyrics="um dois", confirm="true", **fields):
    files = {"audio": audio} if audio else {}
    data = {"lyrics": lyrics, "confirm": confirm, **fields}
    return client.post("/jobs", files=files, data=data)


def wait_for(client, job_id, status, timeout=5, headers=None):
    deadline = time.monotonic() + timeout
    body = {}
    while time.monotonic() < deadline:
        body = client.get(f"/jobs/{job_id}", headers=headers).json()
        if body["status"] == status:
            return body
        time.sleep(0.05)
    raise AssertionError(f"job não chegou a {status}: {body}")


def test_recusa_arquivo_que_nao_e_mp3(client):
    response = send(client, audio=("musica.wav", b"RIFF", "audio/wav"))
    assert response.status_code == 400
    assert "mp3" in response.json()["detail"]


def test_recusa_letra_vazia(client):
    response = send(client, lyrics="   ")
    assert response.status_code == 400
    assert "letra" in response.json()["detail"]


def test_recusa_arquivo_maior_que_25_mb(client):
    response = send(client, audio=("grande.mp3", b"0" * (25 * 1024 * 1024 + 1), "audio/mpeg"))
    assert response.status_code == 413


def test_recusa_envio_sem_confirmacao_de_direitos(client):
    response = send(client, confirm="false")
    assert response.status_code == 400
    assert "autorização" in response.json()["detail"]


def test_recusa_trecho_invertido(client):
    response = send(client, clip_start="30", clip_end="10")
    assert response.status_code == 400


def test_recusa_estilo_desconhecido(client):
    response = send(client, style="rap")
    assert response.status_code == 400


def test_recusa_fundo_desconhecido(client):
    response = send(client, background="radial")
    assert response.status_code == 400
    assert "fundo" in response.json()["detail"]


def test_fundo_escolhido_chega_ao_job(client, monkeypatch):
    def fake_pipeline(job):
        job.video.parent.mkdir(parents=True)
        job.video.write_bytes(b"mp4")
        return 0

    monkeypatch.setattr(jobs, "run_pipeline", fake_pipeline)
    job_id = send(client, background="solid").json()["id"]
    wait_for(client, job_id, "done")
    assert web_app.queue.jobs[job_id].background == "solid"
    assert web_app.queue.jobs[job_id].video.name == "video-karaoke-solid.mp4"  # cada fundo tem seu vídeo


@pytest.mark.parametrize("fundo", ["aurora", "aurora-gl", "sunrise"])
def test_fundo_aurora_e_aceito_pela_web(client, monkeypatch, fundo):
    def fake_pipeline(job):
        job.video.parent.mkdir(parents=True)
        job.video.write_bytes(b"mp4")
        return 0

    monkeypatch.setattr(jobs, "run_pipeline", fake_pipeline)
    job_id = send(client, background=fundo).json()["id"]
    wait_for(client, job_id, "done")
    assert web_app.queue.jobs[job_id].video.name == f"video-karaoke-{fundo}.mp4"


def test_pagina_carrega_o_script_separado(client):
    assert 'src="app.js?v=' in client.get("/").text
    assert client.get("/app.js").status_code == 200



def test_pipeline_recebe_o_fundo_na_linha_de_comando(tmp_path, monkeypatch):
    comandos = []

    class FakeProcess:
        def __init__(self, command, **_kwargs):
            comandos.append(command)
            self.stdout = iter([])

        def wait(self):
            return 0

    monkeypatch.setattr(jobs.subprocess, "Popen", FakeProcess)
    jobs.run_pipeline(jobs.Job("id", tmp_path, tmp_path / "a.mp3", "karaoke", "solid", None))
    command = comandos[0]
    assert command[command.index("--background") + 1] == "solid"


def test_letra_com_quebra_crlf_cai_na_mesma_pasta_do_pipeline(client, monkeypatch):
    def fake_pipeline(job):
        job.video.parent.mkdir(parents=True)
        job.video.write_bytes(b"mp4")
        return 0

    monkeypatch.setattr(jobs, "run_pipeline", fake_pipeline)
    job_id = send(client, lyrics="um\r\ndois").json()["id"]
    wait_for(client, job_id, "done")
    expected = pipeline.make_slug(web_app.queue.jobs[job_id].audio, "um\ndois")  # o que o pipeline calcula
    assert web_app.queue.jobs[job_id].video.parent.name == expected


def test_job_completo_entrega_o_mp4(client, monkeypatch):
    def fake_pipeline(job):
        job.read_line("[1/5] Separando vocais... ok (1 s)")
        job.video.parent.mkdir(parents=True)
        job.video.write_bytes(b"mp4 falso")
        return 0

    monkeypatch.setattr(jobs, "run_pipeline", fake_pipeline)
    job_id = send(client).json()["id"]
    body = wait_for(client, job_id, "done")
    assert body["stage"] == "Concluído"
    assert web_app.queue.jobs[job_id].video.parent.name.startswith("musica-")  # mesmo nome que a linha de comando daria
    video = client.get(f"/jobs/{job_id}/video")
    assert video.status_code == 200
    assert video.content == b"mp4 falso"


def test_erro_da_pipeline_aparece_no_status(client, monkeypatch):
    def failing_pipeline(job):
        job.read_line("[2/5] Alinhando letra... falhou")
        job.read_line("erro: etapa 'Alinhando letra' falhou: modelo indisponível")
        return 1

    monkeypatch.setattr(jobs, "run_pipeline", failing_pipeline)
    job_id = send(client).json()["id"]
    body = wait_for(client, job_id, "error")
    assert body["stage"] == "Alinhando letra"
    assert "modelo indisponível" in body["message"]
    assert client.get(f"/jobs/{job_id}/video").status_code == 409


def test_senha_obrigatoria_quando_configurada(client, monkeypatch):
    def fake_pipeline(job):
        job.video.parent.mkdir(parents=True)
        job.video.write_bytes(b"mp4")
        return 0

    monkeypatch.setattr(jobs, "run_pipeline", fake_pipeline)
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "segredo")
    assert send(client).status_code == 401
    assert send(client).status_code == 401
    job_id = client.post("/jobs", files={"audio": MP3}, data={"lyrics": "um", "confirm": "true"},
                         headers={"X-Access-Token": "segredo"}).json()["id"]
    assert client.get(f"/jobs/{job_id}").status_code == 401
    assert client.get(f"/jobs/{job_id}", headers={"X-Access-Token": "errada"}).status_code == 401
    wait_for(client, job_id, "done", headers={"X-Access-Token": "segredo"})
    assert client.get(f"/jobs/{job_id}/video").status_code == 401
    assert client.get(f"/jobs/{job_id}/video", headers={"X-Access-Token": "segredo"}).status_code == 200


def test_job_desconhecido_da_404(client):
    assert client.get("/jobs/nao-existe").status_code == 404
