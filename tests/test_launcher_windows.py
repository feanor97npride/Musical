# Testes das ações do Windows, sem rodar nada de Windows: o comando é conferido, não executado.
import subprocess
import threading

from web.launcher import windows
from web.launcher.windows import close_handler, install_close_handler, kill_tree, shortcut_command


class ProcessoFalso:
    pid = 1234

    def poll(self):
        return None  # ainda rodando


def test_encerrar_no_windows_usa_taskkill_com_arvore_e_forca(monkeypatch):
    chamadas = []
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: chamadas.append(args))
    kill_tree(ProcessoFalso(), windows=True)
    assert chamadas == [["taskkill", "/PID", "1234", "/T", "/F"]]


def test_atalho_nao_usa_flags_que_disparam_o_defender():
    comando = " ".join(shortcut_command())
    for proibido in ["Bypass", "EncodedCommand", "WindowStyle"]:
        assert proibido not in comando
    assert shortcut_command()[0] == "powershell"


def test_fechar_a_janela_para_o_laco_e_segura_o_processo():
    stop = threading.Event()
    handle = close_handler(stop.set, grace=0)
    assert handle(2) is True  # CTRL_CLOSE_EVENT
    assert stop.is_set()


def test_ctrl_c_segue_o_caminho_normal_do_python():
    stop = threading.Event()
    handle = close_handler(stop.set, grace=0)
    assert handle(0) is False  # CTRL_C_EVENT
    assert not stop.is_set()


def test_fora_do_windows_instalar_o_aviso_nao_faz_nada():
    install_close_handler(lambda: None)
    assert windows._close_routine is None
