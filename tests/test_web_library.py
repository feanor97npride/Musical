# Testes das rotas da biblioteca (pasta do Drive): listagem, geração pela pasta e as recusas.
import pytest
from fastapi.testclient import TestClient

from engine.names import clean_name
from web import app as web_app
from web import jobs


@pytest.fixture
def biblioteca(tmp_path, monkeypatch):
    songs = tmp_path / "entrada"
    folder = songs / "Musica A"
    folder.mkdir(parents=True)
    (folder / "musica.mp3").write_bytes(b"ID3fake")
    (folder / "letra.txt").write_text("[Verse]\numa linha\n[Chorus]\noutra", encoding="utf-8")
    monkeypatch.setenv("DRIVE_INPUT_DIR", str(songs))
    monkeypatch.delenv("DRIVE_OUTPUT_DIR", raising=False)  # sem pasta de saída: a entrega não roda
    monkeypatch.setattr(jobs, "UPLOADS", tmp_path / "uploads")
    monkeypatch.setattr(jobs, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(jobs, "run_pipeline", lambda job: 0)  # o job termina sem vídeo; aqui importa a criação
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "")
    with TestClient(web_app.app) as client:
        yield client


def gerar(client, name="Musica%20A", **fields):
    data = {"confirm": "true", "style": "karaoke", "background": "gradient", "format": "horizontal", "cuts": "", **fields}
    return client.post(f"/biblioteca/{name}/jobs", data=data)


def test_lista_mostra_as_musicas_da_pasta(biblioteca):
    assert biblioteca.get("/biblioteca").json() == {"songs": ["Musica A"]}


def test_sem_pasta_configurada_da_404(biblioteca, monkeypatch):
    monkeypatch.delenv("DRIVE_INPUT_DIR")
    assert biblioteca.get("/biblioteca").status_code == 404


def test_pasta_que_nao_existe_da_409(biblioteca, monkeypatch, tmp_path):
    monkeypatch.setenv("DRIVE_INPUT_DIR", str(tmp_path / "nao-existe"))
    assert biblioteca.get("/biblioteca").status_code == 409


def test_senha_obrigatoria_quando_configurada(biblioteca, monkeypatch):
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "segredo")
    assert biblioteca.get("/biblioteca").status_code == 401
    assert gerar(biblioteca).status_code == 401


def test_gera_a_musica_com_a_letra_da_pasta(biblioteca):
    response = gerar(biblioteca)
    assert response.status_code == 200
    job = web_app.queue.jobs[response.json()["id"]]
    assert job.library_name == "Musica A"
    assert job.audio.stem == clean_name("Musica A")
    assert job.format == "horizontal"
    assert job.lyrics.read_text(encoding="utf-8") == "[Verse]\numa linha\n[Chorus]\noutra"


def test_recusa_sem_confirmacao(biblioteca):
    assert gerar(biblioteca, confirm="false").status_code == 400


def test_recusa_cortes_desconhecidos(biblioteca):
    assert gerar(biblioteca, cuts="7").status_code == 400


def test_musica_que_nao_existe_da_404(biblioteca):
    assert gerar(biblioteca, name="Nao%20existe").status_code == 404


def test_fundo_com_imagem_sem_arquivo_na_pasta_da_400(biblioteca):
    assert gerar(biblioteca, background="image").status_code == 400
