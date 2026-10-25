# Testes do Drive automático sem TXT: transcreve a letra pelo áudio, grava o letra.txt e só então gera os vídeos.
import logging
from types import SimpleNamespace

import pytest

from web import drive_auto, limites


class FilaFalsa:
    def __init__(self) -> None:
        self.jobs: dict = {}
        self.criados: list[tuple] = []
        self.letras: list[tuple] = []
        self.job_letra = SimpleNamespace(status="queued", message="", transcript=None)

    def create(self, *args, **kwargs) -> None:
        self.criados.append((args, kwargs))

    def create_letra(self, filename: str, audio: bytes) -> SimpleNamespace:
        self.letras.append((filename, audio))
        return self.job_letra


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    monkeypatch.setattr(drive_auto, "STATE", tmp_path / "estado" / "drive-auto.json")
    root = tmp_path / "entrada"
    root.mkdir()
    folder = root / "Musica A"
    folder.mkdir()
    (folder / "a.mp3").write_bytes(b"mp3")  # só o MP3: sem TXT
    return root


def varrer(fila, root, state, waiting, transcribing, vezes=1):
    for _ in range(vezes):
        drive_auto.scan_once(fila, root, state, waiting, "full", transcribing)


def test_mp3_sem_txt_so_transcreve_na_segunda_varredura_igual(pasta):
    fila, state, waiting, transcribing = FilaFalsa(), {}, {}, {}
    varrer(fila, pasta, state, waiting, transcribing)
    assert fila.letras == []  # primeira vez que viu: o Drive pode estar gravando
    varrer(fila, pasta, state, waiting, transcribing)
    assert fila.letras == [("Musica A.mp3", b"mp3")]
    assert fila.criados == [] and state == {}  # nenhum vídeo ainda; o estado só é salvo no fim


def test_transcricao_em_andamento_nao_cria_outro_job(pasta):
    fila, transcribing = FilaFalsa(), {}
    varrer(fila, pasta, {}, {}, transcribing, vezes=6)
    assert len(fila.letras) == 1


def test_transcricao_pronta_grava_o_letra_txt_e_depois_gera_os_videos(pasta, tmp_path):
    fila, state, waiting, transcribing = FilaFalsa(), {}, {}, {}
    varrer(fila, pasta, state, waiting, transcribing, vezes=2)
    texto = tmp_path / "transcricao.txt"
    texto.write_text("primeiro verso\nsegundo verso\n", encoding="utf-8")
    fila.job_letra.status, fila.job_letra.transcript = "done", texto
    varrer(fila, pasta, state, waiting, transcribing)
    assert (pasta / "Musica A" / "letra.txt").read_text(encoding="utf-8") == "primeiro verso\nsegundo verso\n"
    assert fila.criados == []  # a pasta agora tem TXT e passa pela regra normal de estabilidade
    varrer(fila, pasta, state, waiting, transcribing, vezes=2)
    assert len(fila.criados) == 2  # full: um job por formato
    assert fila.criados[0][0][2] == "primeiro verso\nsegundo verso\n"
    varrer(fila, pasta, state, waiting, transcribing, vezes=3)
    assert len(fila.criados) == 2 and len(fila.letras) == 1  # nada se repete


def test_transcricao_com_erro_avisa_e_nao_repete(pasta, monkeypatch):
    avisos = []
    monkeypatch.setattr(drive_auto.telegram, "send", avisos.append)
    fila, state, waiting, transcribing = FilaFalsa(), {}, {}, {}
    varrer(fila, pasta, state, waiting, transcribing, vezes=2)
    fila.job_letra.status, fila.job_letra.message = "error", "nenhuma palavra reconhecida"
    varrer(fila, pasta, state, waiting, transcribing, vezes=4)
    assert not (pasta / "Musica A" / "letra.txt").exists()
    assert "Musica A" in state
    assert len(avisos) == 1 and "Musica A" in avisos[0] and "nenhuma palavra" in avisos[0]
    assert len(fila.letras) == 1 and fila.criados == []


def test_fila_cheia_nao_cria_a_transcricao(pasta):
    fila = FilaFalsa()
    fila.jobs = {str(i): SimpleNamespace(status="queued") for i in range(5)}
    varrer(fila, pasta, {}, {}, {}, vezes=3)
    assert fila.letras == []


def test_mp3_grande_demais_nao_transcreve_nem_repete(pasta, monkeypatch, caplog):
    monkeypatch.setattr(limites, "MAX_BYTES", 1)
    fila, state, waiting = FilaFalsa(), {}, {}
    with caplog.at_level(logging.WARNING):
        varrer(fila, pasta, state, waiting, {}, vezes=4)
    assert fila.letras == [] and "Musica A" in state
    assert caplog.text.count("ignorou") == 1


def test_pasta_com_txt_continua_indo_direto_para_os_videos(pasta):
    (pasta / "Musica A" / "a.txt").write_text("letra", encoding="utf-8")
    fila = FilaFalsa()
    varrer(fila, pasta, {}, {}, {}, vezes=2)
    assert fila.letras == [] and len(fila.criados) == 2
