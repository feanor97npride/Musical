# Testes do fundo com imagem enviada: formato, limite de tamanho e caminho passado à pipeline.
import pytest
from fastapi.testclient import TestClient

from web import app as web_app
from web import jobs

MP3 = ("musica.mp3", b"ID3fake", "audio/mpeg")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "UPLOADS", tmp_path / "uploads")
    monkeypatch.setattr(jobs, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "")
    with TestClient(web_app.app) as test_client:
        yield test_client


def test_fundo_imagem_exige_jpg_ou_png(client, monkeypatch):
    monkeypatch.setattr(jobs, "run_pipeline", lambda job: 0)
    data = {"lyrics": "um dois", "confirm": "true", "background": "image"}
    assert client.post("/jobs", files={"audio": MP3}, data=data).status_code == 400
    gif = {"audio": MP3, "background_image": ("foto.gif", b"gif", "image/gif")}
    assert client.post("/jobs", files=gif, data=data).status_code == 400
    png = {"audio": MP3, "background_image": ("foto.png", b"png", "image/png")}
    assert client.post("/jobs", files=png, data=data).status_code == 200


def test_imagem_de_fundo_tem_limite_de_10_mb(client, monkeypatch):
    monkeypatch.setattr(jobs, "run_pipeline", lambda job: 0)
    big = {"audio": MP3, "background_image": ("foto.jpg", b"x" * (10 * 1024 * 1024 + 1), "image/jpeg")}
    data = {"lyrics": "um dois", "confirm": "true", "background": "image"}
    assert client.post("/jobs", files=big, data=data).status_code == 413


def test_fundo_imagem_passa_o_caminho_para_a_pipeline(tmp_path, monkeypatch):
    captured = []

    class FakeProcess:
        stdout: list = []

        def __init__(self, command, **kwargs):
            captured.extend(command)

        def wait(self):
            return 0

    monkeypatch.setattr(jobs.subprocess, "Popen", FakeProcess)
    folder = tmp_path / "job"
    folder.mkdir()
    job = jobs.Job("abc", folder, folder / "m.mp3", "karaoke", "image", None, background_image=folder / "fundo.png")
    jobs.run_pipeline(job)
    assert captured[captured.index("--background-image") + 1] == str(folder / "fundo.png")


def test_formato_desconhecido_e_recusado(client, monkeypatch):
    monkeypatch.setattr(jobs, "run_pipeline", lambda job: 0)
    data = {"lyrics": "um dois", "confirm": "true", "format": "quadrado"}
    assert client.post("/jobs", files={"audio": MP3}, data=data).status_code == 400


def test_formato_horizontal_chega_ao_comando(tmp_path, monkeypatch):
    captured = []

    class FakeProcess:
        stdout: list = []

        def __init__(self, command, **kwargs):
            captured.extend(command)

        def wait(self):
            return 0

    monkeypatch.setattr(jobs.subprocess, "Popen", FakeProcess)
    folder = tmp_path / "job"
    folder.mkdir()
    job = jobs.Job("abc", folder, folder / "m.mp3", "karaoke", "gradient", None, format="horizontal")
    jobs.run_pipeline(job)
    assert captured[captured.index("--format") + 1] == "horizontal"
