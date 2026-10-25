# Testes do Drive automático: só gera música estável e nova, o atalho full cria dois jobs, e nada se repete.
import logging
from types import SimpleNamespace

import pytest

from web import drive_auto, limites


class FilaFalsa:
    def __init__(self) -> None:
        self.jobs: dict = {}
        self.criados: list[tuple] = []

    def create(self, *args, **kwargs) -> None:
        self.criados.append((args, kwargs))


class Parar(BaseException):
    """Sai do loop infinito do watch nos testes."""


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    monkeypatch.setattr(drive_auto, "STATE", tmp_path / "estado" / "drive-auto.json")
    root = tmp_path / "entrada"
    root.mkdir()
    return root


def musica(root, nome="Musica A", letra="primeiro verso", imagem=False):
    folder = root / nome
    folder.mkdir(exist_ok=True)
    (folder / "a.mp3").write_bytes(b"mp3")
    (folder / "a.txt").write_text(letra, encoding="utf-8")
    if imagem:
        (folder / "fundo.jpg").write_bytes(b"img")
    return folder


def varrer(fila, root, state, waiting, vezes=2, preset="full"):
    for _ in range(vezes):
        drive_auto.scan_once(fila, root, state, waiting, preset)


def test_musica_nova_so_e_gerada_na_segunda_varredura_igual(pasta):
    musica(pasta)
    fila, state, waiting = FilaFalsa(), {}, {}
    varrer(fila, pasta, state, waiting, vezes=1)
    assert fila.criados == []  # primeira vez que viu: o Drive pode ainda estar gravando
    varrer(fila, pasta, state, waiting, vezes=1)
    assert len(fila.criados) == 2
    assert "Musica A" in state
    varrer(fila, pasta, state, waiting, vezes=3)
    assert len(fila.criados) == 2  # não gera de novo


def test_arquivo_vazio_espera_o_drive_terminar(pasta):
    folder = musica(pasta)
    (folder / "a.mp3").write_bytes(b"")
    fila = FilaFalsa()
    varrer(fila, pasta, {}, {}, vezes=3)
    assert fila.criados == []


def test_pasta_sem_mp3_ou_com_duas_letras_e_ignorada(pasta):
    sem_mp3 = musica(pasta, "Sem MP3")
    (sem_mp3 / "a.mp3").unlink()
    duas_letras = musica(pasta, "Duas letras")
    (duas_letras / "b.txt").write_text("outra letra", encoding="utf-8")
    fila = FilaFalsa()
    varrer(fila, pasta, {}, {}, vezes=3)
    assert fila.criados == []


def test_full_cria_um_job_por_formato_com_os_parametros_certos(pasta):
    musica(pasta)
    fila = FilaFalsa()
    varrer(fila, pasta, {}, {})
    (args1, kw1), (args2, kw2) = fila.criados
    # (arquivo, letra, estilo, fundo, clip, cortes, imagem, formato)
    assert args1[0] == "Musica A.mp3" and args1[1] == b"mp3" and args1[2] == "primeiro verso"
    assert args1[3:9] == ("karaoke", "gradient", None, None, None, "horizontal")
    assert args2[3:9] == ("karaoke", "gradient", None, 90, None, "vertical")
    assert kw1 == kw2 == {"library_name": "Musica A"}


def test_com_imagem_na_pasta_usa_o_fundo_minha_imagem(pasta):
    musica(pasta, imagem=True)
    fila = FilaFalsa()
    varrer(fila, pasta, {}, {}, preset="yt")
    args, _ = fila.criados[0]
    assert args[4] == "image" and args[7] == (b"img", ".jpg")


def test_tiktok_e_yt_criam_um_job_so(pasta):
    musica(pasta)
    for preset in ("tiktok", "yt"):
        fila = FilaFalsa()
        varrer(fila, pasta, {}, {}, preset=preset)
        assert len(fila.criados) == 1


def test_arquivo_alterado_gera_de_novo(pasta):
    folder = musica(pasta)
    fila, state, waiting = FilaFalsa(), {}, {}
    varrer(fila, pasta, state, waiting)
    (folder / "a.txt").write_text("letra nova e maior", encoding="utf-8")  # tamanho diferente = assinatura nova
    varrer(fila, pasta, state, waiting)
    assert len(fila.criados) == 4


def test_fila_cheia_espera_sem_salvar_o_estado(pasta):
    musica(pasta)
    fila = FilaFalsa()
    fila.jobs = {str(i): SimpleNamespace(status="queued") for i in range(4)}  # 4 esperando + 2 do full > 5
    state: dict = {}
    varrer(fila, pasta, state, {}, vezes=3)
    assert fila.criados == [] and state == {} and not drive_auto.STATE.exists()


def test_mp3_grande_demais_nao_repete_o_erro(pasta, monkeypatch, caplog):
    musica(pasta)
    monkeypatch.setattr(limites, "MAX_BYTES", 1)
    fila, state, waiting = FilaFalsa(), {}, {}
    with caplog.at_level(logging.WARNING):
        varrer(fila, pasta, state, waiting, vezes=4)
    assert fila.criados == []
    assert "Musica A" in state  # a assinatura foi salva: não tenta de novo até a pasta mudar
    assert caplog.text.count("ignorou") == 1


def test_primeira_ativacao_so_registra_o_que_ja_existe(pasta, monkeypatch):
    musica(pasta)
    monkeypatch.setenv("DRIVE_INPUT_DIR", str(pasta))
    monkeypatch.setattr(drive_auto.time, "sleep", lambda segundos: (_ for _ in ()).throw(Parar()))
    fila = FilaFalsa()
    with pytest.raises(Parar):
        drive_auto.watch(fila)
    assert fila.criados == []
    assert "Musica A" in drive_auto.load_state()  # registrada como vista


def test_reiniciar_nao_gera_de_novo_o_que_ja_foi_processado(pasta, monkeypatch):
    musica(pasta)
    drive_auto.save_state(drive_auto.current(pasta))  # estado de uma execução anterior
    monkeypatch.setenv("DRIVE_INPUT_DIR", str(pasta))
    chamadas = {"n": 0}

    def dormir(segundos):
        chamadas["n"] += 1
        if chamadas["n"] >= 3:
            raise Parar()

    monkeypatch.setattr(drive_auto.time, "sleep", dormir)
    fila = FilaFalsa()
    with pytest.raises(Parar):
        drive_auto.watch(fila)
    assert fila.criados == []


def test_estado_quebrado_conta_como_primeira_ativacao(pasta):
    drive_auto.STATE.parent.mkdir(parents=True)
    drive_auto.STATE.write_text("{ não é json", encoding="utf-8")
    assert drive_auto.load_state() is None


def test_atalho_invalido_nao_inicia_a_thread(pasta, monkeypatch, caplog):
    monkeypatch.setenv("DRIVE_INPUT_DIR", str(pasta))
    monkeypatch.setenv("DRIVE_AUTO_PRESET", "inexistente")
    drive_auto.watch(FilaFalsa())  # volta na hora, sem loop
    assert "DRIVE_AUTO_PRESET" in caplog.text
