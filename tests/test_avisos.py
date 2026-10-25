# Testes dos avisos: só job de vídeo terminado, só da pasta do Drive por padrão, e uma mensagem por job.
from pathlib import Path

from web import avisos
from web.jobs import Job, JobQueue


def job(**campos) -> Job:
    base = dict(id="a", folder=Path("."), audio=Path("musica-a.mp3"), style="karaoke", background="gradient", clip=None,
                status="done", finished=1.0, library_name="Musica A")
    return Job(**{**base, **campos})


def test_so_avisa_job_de_video_que_terminou(monkeypatch):
    assert avisos.should_notify(job())
    assert avisos.should_notify(job(status="error", message="falhou"))
    assert not avisos.should_notify(job(finished=0.0))  # ainda não terminou: a cópia para o Drive pode estar rodando
    assert not avisos.should_notify(job(kind="letra"))
    assert not avisos.should_notify(job(cancelled=True))  # cancelar foi decisão do usuário


def test_por_padrao_so_avisa_musica_da_pasta_do_drive(monkeypatch):
    assert not avisos.should_notify(job(library_name=None))
    monkeypatch.setenv("TELEGRAM_NOTIFY", "all")
    assert avisos.should_notify(job(library_name=None))


def test_mensagem_de_video_pronto_traz_nome_formato_e_quantidade():
    pronto = job(format="horizontal", ready_videos=[Path("a.mp4")])
    assert avisos.message(pronto) == "Vídeo pronto: Musica A (16:9, 1 arquivo(s))"


def test_mensagem_de_pronto_inclui_o_aviso_da_copia_para_o_drive():
    pronto = job(ready_videos=[Path("a.mp4")], message="aviso: não consegui copiar para a pasta do Drive")
    assert pronto.message in avisos.message(pronto)


def test_mensagem_de_erro_traz_o_motivo():
    assert avisos.message(job(status="error", message="a pipeline terminou com código 1")) == (
        "Erro ao gerar Musica A (9:16): a pipeline terminou com código 1")


def test_envio_sem_pasta_do_drive_usa_o_nome_do_mp3(monkeypatch):
    monkeypatch.setenv("TELEGRAM_NOTIFY", "all")
    assert "musica-a" in avisos.message(job(library_name=None))


def test_cada_job_e_avisado_uma_vez_so(monkeypatch):
    enviados = []
    monkeypatch.setattr(avisos.telegram, "send", enviados.append)
    queue = JobQueue()
    queue.jobs["a"] = job()
    seen: set[str] = set()
    avisos.notify_new(queue, seen)
    avisos.notify_new(queue, seen)
    assert len(enviados) == 1
