# Testes do envio com vídeo (MP4 com a música): aceita com som, recusa sem som, recusa acima de 100 MB e gera o job.
import subprocess
import time

import pytest
from fastapi.testclient import TestClient

from web import app as web_app
from web import jobs, video_in

pytestmark = pytest.mark.skipif(video_in.shutil.which("ffmpeg") is None, reason="precisa do ffmpeg")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "UPLOADS", tmp_path / "uploads")
    monkeypatch.setattr(jobs, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(web_app, "ACCESS_TOKEN", "")
    with TestClient(web_app.app) as test_client:
        yield test_client


def video_bytes(tmp_path, com_som=True):
    path = tmp_path / "entrada.mp4"
    comando = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=2"]
    if com_som:
        comando += ["-f", "lavfi", "-i", "sine=frequency=440:duration=2"]
    comando += ["-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(comando, check=True)
    return path.read_bytes()


def enviar(client, data, nome="musica.mp4", lyrics="um dois", **campos):
    return client.post("/jobs", files={"audio": (nome, data, "video/mp4")},
                       data={"lyrics": lyrics, "confirm": "true", "background": "video", **campos})


def esperar(client, job_id, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/jobs/{job_id}").json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.1)
    raise AssertionError("job não terminou")


def test_aceita_mp4_com_som_e_cria_o_job(client, tmp_path, monkeypatch):
    def pipeline_falsa(job):  # o motor de verdade (Demucs, Whisper, render) não roda no teste
        job.video.parent.mkdir(parents=True)
        job.video.write_bytes(b"mp4")
        return 0

    monkeypatch.setattr(jobs, "run_pipeline", pipeline_falsa)
    resposta = enviar(client, video_bytes(tmp_path), format="horizontal")
    assert resposta.status_code == 200
    job = esperar(client, resposta.json()["id"])
    assert job["kind"] == "video"  # o job de vídeo entra na fila e é processado como os outros


def test_recusa_mp4_sem_som(client, tmp_path):
    resposta = enviar(client, video_bytes(tmp_path, com_som=False))
    assert resposta.status_code == 400
    assert "som" in resposta.json()["detail"]


def test_recusa_mp4_acima_do_limite(client, tmp_path, monkeypatch):
    monkeypatch.setattr(web_app, "MAX_VIDEO_BYTES", 1000)  # a rota lê o limite de web_app, não do módulo limites
    resposta = enviar(client, video_bytes(tmp_path))
    assert resposta.status_code == 413


def test_recusa_arquivo_com_extensao_mp4_que_nao_e_video(client):
    resposta = enviar(client, b"isto nao e um video")
    assert resposta.status_code == 400
    assert "MP4 válido" in resposta.json()["detail"]


def test_recusa_extensao_que_nao_e_mp3_nem_mp4(client):
    resposta = client.post("/jobs", files={"audio": ("musica.wav", b"x", "audio/wav")},
                           data={"lyrics": "um", "confirm": "true"})
    assert resposta.status_code == 400
    assert ".mp3 ou .mp4" in resposta.json()["detail"]
