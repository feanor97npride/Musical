# Testes da opção de cortes na web: recusas do envio, comando da pipeline e download de cada corte.
import io
import json
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

from engine.cuts import plan_cuts
from engine.export import exported_path, part_name
from engine.names import variant_name
from web import app as web_app
from web import jobs, runner

MP3 = ("musica.mp3", b"ID3fake", "audio/mpeg")
# versos de 5 s; seção muda no 7º e no 13º verso, para os capítulos terem tempos diferentes de zero
CORTES_SONG = {"audio": {"duration": 100.0},
               "lines": [{"start": i * 5.0, "end": i * 5.0 + 4.0, "section": "chorus" if 6 <= i < 12 else "verse"}
                         for i in range(18)]}
DRAFT = {"youtube_title": "Manhã de fé", "youtube_description": "Uma música de esperança.",
         "tiktok_caption": "Depois da noite vem o sol", "hashtags": ["#gospel", "#louvor", "#fe"]}


def copiar_para_postar(path, audio):
    """Cria a cópia para postar que a pipeline com --export gravaria ao lado do vídeo."""
    copy = exported_path(path, audio)
    copy.parent.mkdir(exist_ok=True)
    copy.write_bytes(b"copia " + path.name.encode())


def gerar_cortes(job):
    job.video.parent.mkdir(parents=True)
    (job.video.parent / "song.json").write_text(json.dumps(CORTES_SONG), encoding="utf-8")
    for clip in plan_cuts(CORTES_SONG, job.cuts):  # nomes calculados aqui, sem depender de Job.videos
        path = job.video.parent / f"video-{variant_name('karaoke', 'gradient', clip)}.mp4"
        path.write_bytes(b"mp4 " + path.name.encode())
        copiar_para_postar(path, job.audio)
    return 0


def gerar_video_unico(job):  # sem song.json de propósito: o pacote tem que sair mesmo assim
    job.video.parent.mkdir(parents=True)
    job.video.write_bytes(b"mp4 unico")
    copiar_para_postar(job.video, job.audio)
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


def test_aceita_cortes_de_noventa_segundos(client, monkeypatch):
    monkeypatch.setattr(jobs, "run_pipeline", gerar_cortes)
    response = send(client, cuts="90")
    assert response.status_code == 200
    wait_for(client, response.json()["id"], "done")


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

    monkeypatch.setattr(runner.subprocess, "Popen", FakeProcess)
    jobs.run_pipeline(jobs.Job("id", tmp_path, tmp_path / "a.mp3", "karaoke", "solid", None, cuts=30))
    assert comandos[0][-2:] == ["--cuts", "30"]
    assert "--export" in comandos[0]  # o pacote para postar usa a cópia exportada


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


def test_pacote_tem_as_copias_com_nomes_legiveis_e_postar_txt(client, monkeypatch):
    monkeypatch.setattr(jobs, "run_pipeline", gerar_cortes)
    job_id = send(client, cuts="30").json()["id"]
    wait_for(client, job_id, "done")
    job = web_app.queue.jobs[job_id]
    job.status = "running"  # o job já terminou: forço o estado para checar a recusa
    assert client.get(f"/jobs/{job_id}/pacote.zip").status_code == 409
    job.status = "done"
    response = client.get(f"/jobs/{job_id}/pacote.zip")
    assert response.status_code == 200 and "musica-pacote.zip" in response.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist() == ["01-musica-parte-1-de-3.mp4", "02-musica-parte-2-de-3.mp4",
                                      "03-musica-parte-3-de-3.mp4", "postar.txt"]
        assert archive.read("02-musica-parte-2-de-3.mp4") == exported_path(job.ready_videos[1], job.audio).read_bytes()
        assert "00:30 Refrão" in archive.read("postar.txt").decode("utf-8-sig")
    assert (job.folder / "pacote.zip").exists()  # a próxima chamada reaproveita este arquivo


def test_pacote_leva_os_textos_de_cada_parte(client, monkeypatch):
    monkeypatch.setattr(jobs, "run_pipeline", gerar_cortes)
    job_id = send(client, cuts="30", draft=json.dumps(DRAFT)).json()["id"]
    wait_for(client, job_id, "done")
    with zipfile.ZipFile(io.BytesIO(client.get(f"/jobs/{job_id}/pacote.zip").content)) as archive:
        text = archive.read("postar.txt").decode("utf-8-sig")
    assert "Título: Parte 1/3 · Manhã de fé" in text
    assert "Legenda: Parte 2/3 · Depois da noite vem o sol" in text
    assert "Descrição do YouTube (com capítulos):\nUma música de esperança.\n\n00:00 Estrofe\n00:30 Refrão" in text


def test_textos_para_postar_invalidos_sao_recusados(client):
    assert send(client, draft="{não é json").status_code == 400
    assert send(client, draft='{"youtube_title": "só um campo"}').status_code == 400
    assert send(client, draft=json.dumps({**DRAFT, "hashtags": ["sem", "jogo"]})).status_code == 400


def test_pacote_de_video_unico_sem_song_json(client, monkeypatch):
    monkeypatch.setattr(jobs, "run_pipeline", gerar_video_unico)
    job_id = send(client).json()["id"]
    wait_for(client, job_id, "done")
    with zipfile.ZipFile(io.BytesIO(client.get(f"/jobs/{job_id}/pacote.zip").content)) as archive:
        assert archive.namelist() == ["musica.mp4", "postar.txt"]
        assert archive.read("postar.txt").decode("utf-8-sig") == "Arquivo: musica.mp4\n"
