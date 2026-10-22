# Rotas do histórico: lista, abrir e apagar, com senha e com o arquivo de teste.
import pytest
from fastapi.testclient import TestClient

from web import app as web_app
from web import history

DRAFT = {"title": "Manhã", "lyrics": "[Chorus]\num", "style": "acoustic pop", "youtube_title": "Manhã de fé",
         "youtube_description": "Uma música de esperança.", "tiktok_caption": "Depois da noite", "hashtags": ["#gospel"]}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY_FILE", tmp_path / "letras.json")
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "")
    monkeypatch.setattr(web_app, "write_lyrics", lambda context: DRAFT)
    return TestClient(web_app.app)


def test_letra_gerada_aparece_na_lista_e_abre_com_a_letra(client):
    item_id = client.post("/lyrics", data={"context": "uma manhã de fé"}).json()["id"]
    assert [item["id"] for item in client.get("/historico").json()] == [item_id]
    opened = client.get(f"/historico/{item_id}").json()
    assert opened["context"] == "uma manhã de fé" and opened["lyrics"] == DRAFT["lyrics"]


def test_apagar_tira_da_lista_e_repete_da_404(client):
    item_id = client.post("/lyrics", data={"context": "c"}).json()["id"]
    assert client.delete(f"/historico/{item_id}").status_code == 204
    assert client.get("/historico").json() == []
    assert client.get(f"/historico/{item_id}").status_code == 404
    assert client.delete(f"/historico/{item_id}").status_code == 404


def test_rotas_do_historico_pedem_a_senha(client, monkeypatch):
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "segredo")
    assert client.get("/historico").status_code == 401
    assert client.get("/historico/x").status_code == 401
    assert client.delete("/historico/x").status_code == 401
    assert client.get("/historico", headers={"X-Access-Token": "segredo"}).status_code == 200
