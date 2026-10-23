# Testes da fila: erros não param a fila nem derrubam job pronto; jobs antigos saem; fila cheia recusa; render travado morre.
import os
import threading
import time
from types import SimpleNamespace

import pytest

from web import jobs, runner
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
    job = SimpleNamespace(id="abc", message="")
    queue._deliver(job)  # não pode levantar: o job já está pronto no PC
    assert "não consegui copiar o job abc" in caplog.text
    assert "copiar para a pasta do Drive" in job.message  # o aviso chega à página pela mensagem do job


def test_jobs_antigos_saem_da_memoria_e_do_disco(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "UPLOADS", tmp_path)
    queue = JobQueue()
    antigo = queue.create_letra("a.mp3", b"x")
    antigo.status, antigo.finished = "done", time.time() - jobs.MAX_AGE - 1
    queue.create_letra("b.mp3", b"y")  # o envio novo dispara a limpeza
    assert antigo.id not in queue.jobs
    assert not antigo.folder.exists()


def test_fila_cheia_recusa_o_envio(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "UPLOADS", tmp_path)
    monkeypatch.setattr(jobs, "MAX_PENDING", 2)
    queue = JobQueue()  # sem start: os envios ficam esperando
    queue.create_letra("a.mp3", b"x")
    queue.create_letra("b.mp3", b"y")
    with pytest.raises(jobs.QueueFull):
        queue.create_letra("c.mp3", b"z")


def test_reinicio_apaga_pastas_antigas_de_envios(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "UPLOADS", tmp_path)
    antiga = tmp_path / "antiga"
    antiga.mkdir()
    os.utime(antiga, (0, 0))  # modificada em 1970: passou do prazo
    nova = tmp_path / "nova"
    nova.mkdir()
    JobQueue().start()  # a memória começa vazia: a pasta antiga não tem dono
    assert not antiga.exists()
    assert nova.exists()


def test_job_cancelado_antes_de_comecar_nao_roda(tmp_path, monkeypatch):
    def nao_deve_rodar(*args, **kwargs):
        raise AssertionError("o processo não devia ter começado")

    monkeypatch.setattr(runner.subprocess, "Popen", nao_deve_rodar)
    job = jobs.Job("id", tmp_path, tmp_path / "a.mp3", "karaoke", "solid", None, cancelled=True)
    assert runner.run_pipeline(job) == 1


def test_processo_que_passa_do_tempo_e_morto(tmp_path, monkeypatch):
    morto = threading.Event()

    class Travado:
        def __init__(self, *args, **kwargs):
            self.pid = 1
            self.stdout = self._saida()

        def _saida(self):
            morto.wait(5)  # a saída só termina quando o processo é morto
            yield from ()

        def wait(self):
            return 1

    monkeypatch.setattr(runner.subprocess, "Popen", Travado)
    monkeypatch.setattr(runner, "kill_tree", lambda process: morto.set())
    monkeypatch.setattr(runner, "JOB_TIMEOUT", 0.1)
    job = jobs.Job("id", tmp_path, tmp_path / "a.mp3", "karaoke", "solid", None)
    assert runner.run_pipeline(job) == 1
    assert morto.is_set()
