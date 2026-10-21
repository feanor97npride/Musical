# Testes da opção de cortes na web: recusas do envio, comando da pipeline e download de cada corte.
import io
import json
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

from engine.cuts import plan_cuts
from engine.names import variant_name
from web import app as web_app
from web import jobs

MP3 = ("musica.mp3", b"ID3fake", "audio/mpeg")
CORTES_SONG = {"audio": {"duration": 100.0}, "lines": [{"start": i * 5.0, "end": i * 5.0 + 4.0} for i in range(18)]}


def gerar_cortes(job):
    job.video.parent.mkdir(parents=True)
    (job.video.parent / "song.json").write_text(json.dumps(CORTES_SONG), encoding="utf-8")
    for clip in plan_cuts(CORTES_SONG, 30.0):  # nomes calculados aqui, sem depender de Job.videos
        path = job.video.parent / f"video-{variant_name('karaoke', 'gradient', clip)}.mp4"
        path.write_bytes(b"mp4 " + path.name.encode())
    return 0


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
    monkeypatch.setattr(jobs, "run_pipeline", gerar_cortes)
    job_id = send(client, cuts="30").json()["id"]
    names = wait_for(client, job_id, "done")["videos"]
    assert len(names) == 3
    assert names[1].startswith("video-karaoke-gradient-")
    response = client.get(f"/jobs/{job_id}/video", params={"n": 1})
    assert response.status_code == 200
    assert response.content == b"mp4 " + names[1].encode()
    assert client.get(f"/jobs/{job_id}/video", params={"n": 3}).status_code == 404


def test_video_sem_numero_em_job_de_cortes_e_recusado(client, monkeypatch):
    monkeypatch.setattr(jobs, "run_pipeline", gerar_cortes)
    job_id = send(client, cuts="30").json()["id"]
    wait_for(client, job_id, "done")
    assert client.get(f"/jobs/{job_id}/video").status_code == 400


def test_lista_de_cortes_fica_mesmo_sem_song_json(client, monkeypatch):
    monkeypatch.setattr(jobs, "run_pipeline", gerar_cortes)
    job_id = send(client, cuts="30").json()["id"]
    names = wait_for(client, job_id, "done")["videos"]
    (web_app.queue.jobs[job_id].video.parent / "song.json").unlink()
    assert wait_for(client, job_id, "done")["videos"] == names
    assert client.get(f"/jobs/{job_id}/video", params={"n": 0}).status_code == 200


def test_zip_com_todos_os_cortes(client, monkeypatch):
    monkeypatch.setattr(jobs, "run_pipeline", gerar_cortes)
    job_id = send(client, cuts="30").json()["id"]
    wait_for(client, job_id, "done")
    job = web_app.queue.jobs[job_id]
    job.status = "running"  # o job já terminou: forço o estado para checar a recusa
    assert client.get(f"/jobs/{job_id}/cortes.zip").status_code == 409
    job.status = "done"
    response = client.get(f"/jobs/{job_id}/cortes.zip")
    assert response.status_code == 200 and "musica-cortes.zip" in response.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist() == [path.name for path in job.ready_videos]
        assert archive.read(job.ready_videos[1].name) == job.ready_videos[1].read_bytes()
    assert (job.folder / "cortes.zip").exists()  # a próxima chamada reaproveita este arquivo
