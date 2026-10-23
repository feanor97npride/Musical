# Testes do segundo formato do preset full: a rota /jobs/{id}/variante copia a música e cria outro job.
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from web import app as web_app
from web import jobs

STATIC = Path(__file__).resolve().parents[1] / "web" / "static"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "UPLOADS", tmp_path / "uploads")
    monkeypatch.setattr(jobs, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(jobs, "run_pipeline", lambda job: 0)  # o job termina sem vídeo; aqui só importa a criação
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "")
    with TestClient(web_app.app) as test_client:
        yield test_client


def criar_job(client, lyrics="uma letra"):
    response = client.post("/jobs", files={"audio": ("musica.mp3", b"ID3fake", "audio/mpeg")},
                           data={"lyrics": lyrics, "confirm": "true", "format": "horizontal"})
    assert response.status_code == 200
    return response.json()["id"]


def test_variante_cria_outro_job_com_a_mesma_letra_e_formato_pedido(client):
    original = criar_job(client, lyrics="linha um\nlinha dois")
    response = client.post(f"/jobs/{original}/variante", data={"format": "vertical", "cuts": "90"})
    assert response.status_code == 200
    nova = web_app.queue.jobs[response.json()["id"]]
    base = web_app.queue.jobs[original]
    assert nova.id != original
    assert nova.format == "vertical"
    assert nova.cuts == 90
    assert nova.lyrics.read_text(encoding="utf-8") == base.lyrics.read_text(encoding="utf-8")
    assert nova.audio.read_bytes() == b"ID3fake"


def test_variante_recusa_formato_e_corte_desconhecidos(client):
    original = criar_job(client)
    assert client.post(f"/jobs/{original}/variante", data={"format": "quadrado"}).status_code == 400
    assert client.post(f"/jobs/{original}/variante", data={"format": "vertical", "cuts": "7"}).status_code == 400


def test_variante_de_job_inexistente_da_404(client):
    assert client.post("/jobs/nao-existe/variante", data={"format": "vertical"}).status_code == 404


def test_variante_exige_senha_quando_ela_esta_configurada(client, monkeypatch):
    original = criar_job(client)
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "senha-certa")
    assert client.post(f"/jobs/{original}/variante", data={"format": "vertical"}).status_code == 401


def test_presets_da_pagina_usam_valores_que_o_servidor_aceita():
    script = (STATIC / "presets.js").read_text(encoding="utf-8")
    formats = set(re.findall(r'format: "(\w+)"', script))
    cuts = set(re.findall(r'cuts: "(\d*)"', script))
    assert formats and cuts
    assert formats <= {"vertical", "horizontal"}
    assert cuts <= set(web_app.CUTS)
