# Testes da fila: um erro fora da pipeline ou na entrega não pode parar a fila nem derrubar um job pronto.
import time
from types import SimpleNamespace

from web import jobs
from web.jobs import JobQueue


def esperar(job, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if job.status in ("done", "error"):
            return job.status
        time.sleep(0.05)
    raise AssertionError(f"job parado em {job.status}")


def test_erro_inesperado_num_job_nao_para_o_proximo(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "UPLOADS", tmp_path / "uploads")
    monkeypatch.setattr(jobs, "run_pipeline", lambda job: 0)  # sem o arquivo da letra, o job termina com erro
    queue = JobQueue()
    real = queue._execute
    chamadas = []

    def falha_no_primeiro(job):
        chamadas.append(job)
        if len(chamadas) == 1:
            raise RuntimeError("bug fora da pipeline")
        real(job)

    queue._execute = falha_no_primeiro
    primeiro = queue.create_letra("a.mp3", b"x")
    segundo = queue.create_letra("b.mp3", b"y")
    queue.start()
    assert esperar(primeiro) == "error"
    assert primeiro.message.startswith("erro inesperado")
    assert esperar(segundo) == "error"  # chegou a rodar: a fila não parou


def test_entrega_com_erro_qualquer_nao_derruba_o_job(caplog):
    queue = JobQueue()

    def song_json_quebrado(job):
        raise ValueError("song.json inválido")

    queue.on_ready = song_json_quebrado
    queue._deliver(SimpleNamespace(id="abc"))  # não pode levantar: o job já está pronto no PC
    assert "não consegui copiar o job abc" in caplog.text
