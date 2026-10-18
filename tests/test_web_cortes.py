# Testes da opção de cortes na web: recusas do envio, comando da pipeline e download de cada corte.
import json
import time

import pytest
from fastapi.testclient import TestClient

from web import app as web_app
from web import jobs

MP3 = ("musica.mp3", b"ID3fake", "audio/mpeg")
CORTES_SONG = {"audio": {"duration": 100.0}, "lines": [{"start": i * 5.0, "end": i * 5.0 + 4.0} for i in range(18)]}


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


def wait_for(client, job_id, status, timeout=5):
    deadline = time.monotonic() + timeout
    body = {}
    while time.monotonic() < deadline:
        body = client.get(f"/jobs/{job_id}").json()
        if body["status"] == status:
            return body
        time.sleep(0.05)
    raise AssertionError(f"job não chegou a {status}: {body}")


def test_recusa_duracao_de_corte_desconhecida(client):
    response = send(client, cuts="7")
    assert response.status_code == 400
    assert "corte" in response.json()["detail"]


def test_recusa_cortes_junto_com_trecho(client):
    response = send(client, cuts="30", clip_start="0", clip_end="10")
    assert response.status_code == 400


def test_cortes_chegam_ao_comando(tmp_path, monkeypatch):
    comandos = []

    class FakeProcess:
        def __init__(self, command, **_kwargs):
            comandos.append(command)
            self.stdout = iter([])

        def wait(self):
            return 0

    monkeypatch.setattr(jobs.subprocess, "Popen", FakeProcess)
    jobs.run_pipeline(jobs.Job("id", tmp_path, tmp_path / "a.mp3", "karaoke", "solid", None, cuts=30))
    assert comandos[0][-2:] == ["--cuts", "30"]


def test_status_lista_os_cortes_e_baixa_um_por_vez(client, monkeypatch):
    def fake_pipeline(job):
        job.video.parent.mkdir(parents=True)
        (job.video.parent / "song.json").write_text(json.dumps(CORTES_SONG), encoding="utf-8")
        for path in job.videos:  # os mesmos nomes que o pipeline grava
            path.write_bytes(b"mp4 " + path.name.encode())
        return 0

    monkeypatch.setattr(jobs, "run_pipeline", fake_pipeline)
    job_id = send(client, cuts="30").json()["id"]
    names = wait_for(client, job_id, "done")["videos"]
    assert len(names) == 3
    assert names[1].startswith("video-karaoke-gradient-")
    response = client.get(f"/jobs/{job_id}/video", params={"n": 1})
    assert response.status_code == 200
    assert response.content == b"mp4 " + names[1].encode()
    assert client.get(f"/jobs/{job_id}/video", params={"n": 3}).status_code == 404
