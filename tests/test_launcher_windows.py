# Testes das ações do Windows, sem rodar nada de Windows: o comando é conferido, não executado.
import subprocess

from web.launcher.windows import kill_tree, shortcut_command


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
