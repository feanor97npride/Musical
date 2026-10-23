# Testes da letra pelo áudio no servidor: envio do MP3, acompanhamento pela fila e download do texto gerado.
import time

import pytest
from fastapi.testclient import TestClient

from web import app as web_app
from web import jobs
from web import letra as letra_module


def fake_transcricao(job):
    job.transcript.write_text("primeira linha\nsegunda linha\n", encoding="utf-8")  # o que o engine.transcribe gravaria
    return 0


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "UPLOADS", tmp_path / "uploads")
    monkeypatch.setattr(jobs, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(jobs, "run_pipeline", fake_transcricao)
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "")
    with TestClient(web_app.app) as test_client:
        yield test_client


def enviar(client, name="musica.mp3"):
    return client.post("/letra", files={"audio": (name, b"ID3fake", "audio/mpeg")})


def esperar(client, job_id, status="done", timeout=5):
    deadline = time.monotonic() + timeout
    body = {}
    while time.monotonic() < deadline:
        body = client.get(f"/jobs/{job_id}").json()
        if body["status"] == status:
            return body
        time.sleep(0.05)
    raise AssertionError(f"job não chegou a {status}: {body}")


def test_letra_gerada_pelo_audio_volta_como_texto(client):
    response = enviar(client)
    assert response.status_code == 200
    job_id = response.json()["id"]
    assert esperar(client, job_id)["kind"] == "letra"
    text = client.get(f"/jobs/{job_id}/letra")
    assert text.status_code == 200
    assert text.text == "primeira linha\nsegunda linha\n"


def test_recusa_arquivo_que_nao_e_mp3(client):
    response = client.post("/letra", files={"audio": ("musica.wav", b"x", "audio/wav")})
    assert response.status_code == 400


def test_letra_antes_de_pronta_da_409(client, monkeypatch):
    monkeypatch.setattr(jobs, "run_pipeline", lambda job: 1)  # o job termina sem gerar nada
    job_id = enviar(client).json()["id"]
    esperar(client, job_id, status="error")
    assert client.get(f"/jobs/{job_id}/letra").status_code == 409


def test_cancelar_mata_o_processo_em_andamento(client, monkeypatch):
    mortos = []

    def render_travado(job):  # só termina quando o cancelamento chega
        job.process = object()
        while not job.cancelled:
            time.sleep(0.01)
        return 1

    monkeypatch.setattr(jobs, "run_pipeline", render_travado)
    monkeypatch.setattr(letra_module, "kill_tree", mortos.append)
    job_id = enviar(client).json()["id"]
    while client.get(f"/jobs/{job_id}").json()["status"] != "running":
        time.sleep(0.01)
    assert client.post(f"/jobs/{job_id}/cancelar").status_code == 200
    assert esperar(client, job_id, status="error")["message"] == "cancelado pelo usuário"
    assert len(mortos) == 1


def test_cancelar_job_terminado_da_409(client):
    job_id = enviar(client).json()["id"]
    esperar(client, job_id)  # a letra fingida termina como "done"
    assert client.post(f"/jobs/{job_id}/cancelar").status_code == 409


def test_fila_cheia_responde_429(client, monkeypatch):
    monkeypatch.setattr(jobs, "MAX_PENDING", 0)  # sem vaga: o envio é recusado com 429
    assert enviar(client).status_code == 429


def test_letra_exige_senha_quando_configurada(client, monkeypatch):
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "segredo")
    assert enviar(client).status_code == 401
