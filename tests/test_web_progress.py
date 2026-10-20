# Testes do progresso do job: etapa lida de "[n/total]", quadros do render, e a barra que nunca volta.
from pathlib import Path

import pytest

from web.jobs import Job


@pytest.fixture
def job(tmp_path: Path) -> Job:
    return Job("id", tmp_path, tmp_path / "a.mp3", "karaoke", "gradient", None)


def test_linha_de_etapa_guarda_numero_total_e_nome(job):
    job.read_line("[3/7] Alinhando letra... ok (55 s)")
    assert (job.step, job.total, job.stage) == (3, 7, "Alinhando letra")
    assert job.progress == pytest.approx(2 / 7)


def test_etapa_com_dois_digitos(job):
    job.read_line("[10/12] Exportando para postar...")
    assert (job.step, job.total) == (10, 12)


def test_quadros_do_render_avancam_dentro_da_etapa(job):
    job.read_line("[6/7] Renderizando vídeo...")
    job.read_line("Rendered 50/100")
    assert job.progress == pytest.approx(5.5 / 7)
    assert job.message == "quadro 50 de 100"


def test_progresso_nunca_diminui(job):
    job.read_line("[6/7] Renderizando vídeo...")
    job.read_line("Rendered 90/100")
    before = job.progress
    job.read_line("Rendered 5/100")  # o próximo corte recomeça a contar quadros
    assert job.progress == before


def test_quadros_sem_etapa_conhecida_nao_quebram(job):
    job.read_line("Rendered 10/0")
    job.read_line("Rendered 10/100")
    assert job.progress == 0.0


def test_to_dict_traz_etapa_total_e_progresso(job):
    job.read_line("[2/7] Alinhando letra...")
    data = job.to_dict()
    assert (data["step"], data["total"], data["progress"]) == (2, 7, round(1 / 7, 3))
