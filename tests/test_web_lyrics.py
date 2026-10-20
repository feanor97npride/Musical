# Testes da rota /lyrics: senha, recusas e erros, com write_lyrics trocado por um falso.
import pytest
from fastapi.testclient import TestClient

from web import app as web_app

DRAFT = {"title": "Manhã", "lyrics": "[Chorus]\num\ndois\ntrês\nquatro", "style": "acoustic pop"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "")  # um .env com senha não pode mudar os testes
    return TestClient(web_app.app)


def test_contexto_vira_letra(client, monkeypatch):
    seen = []
    monkeypatch.setattr(web_app, "write_lyrics", lambda context: seen.append(context) or DRAFT)
    response = client.post("/lyrics", data={"context": "uma música sobre a manhã"})
    assert response.status_code == 200
    assert response.json() == DRAFT
    assert seen == ["uma música sobre a manhã"]


def test_contexto_invalido_da_400_sem_chamar_a_api(client):
    response = client.post("/lyrics", data={"context": "   "})  # o write_lyrics real recusa antes da API
    assert response.status_code == 400
    assert "vazio" in response.json()["detail"]


def test_falta_de_chave_da_503_com_a_mensagem(client, monkeypatch):
    def failing(_context):
        raise RuntimeError("falta THEME_API_KEY no .env para gerar a letra")

    monkeypatch.setattr(web_app, "write_lyrics", failing)
    response = client.post("/lyrics", data={"context": "c"})
    assert response.status_code == 503
    assert "THEME_API_KEY" in response.json()["detail"]


def test_senha_obrigatoria_quando_configurada(client, monkeypatch):
    monkeypatch.setattr(web_app, "write_lyrics", lambda context: DRAFT)
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "segredo")
    assert client.post("/lyrics", data={"context": "c"}).status_code == 401
    ok = client.post("/lyrics", data={"context": "c"}, headers={"X-Access-Token": "segredo"})
    assert ok.status_code == 200
