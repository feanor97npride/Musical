# Ações do Windows: encerrar a árvore de processos, copiar, criar o atalho e tratar o X da janela.
import ctypes
import os
import signal
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

SHORTCUT_SCRIPT = (
    "$d=[Environment]::GetFolderPath('Desktop');"
    "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Gerador de lyric video.lnk'));"
    "$s.TargetPath=$env:LV_TARGET;$s.WorkingDirectory=$env:LV_ROOT;"
    "$s.IconLocation='shell32.dll,13';$s.Save()"
)
CTRL_CLOSE_EVENT = 2  # o Windows manda este aviso quando a janela é fechada pelo X
# atalho: espera fixa de 4 s; o Windows encerra o processo perto de 5 s.
# Se a limpeza passar disso, trocar por um evento.
CLOSE_GRACE = 4.0
_close_routine = None  # guarda a referência: sem ela o coletor de lixo apaga o callback


def kill_tree(proc: subprocess.Popen, windows: bool = os.name == "nt") -> None:
    """Encerra o processo e tudo que ele abriu (python, npm, node, Chrome)."""
    if proc.poll() is not None:
        return
    if windows:  # /T leva junto os filhos; sem /F o console não encerra
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)  # o processo foi criado com start_new_session
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
    except ProcessLookupError:
        return


def copy_to_clipboard(text: str) -> bool:
    """Copia para a área de transferência do Windows. No resto não faz nada."""
    if os.name != "nt":
        return False
    try:
        subprocess.run(["clip"], input=text.encode("ascii", "ignore"), check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def shortcut_command() -> list[str]:
    # sem -ExecutionPolicy Bypass, -EncodedCommand ou -WindowStyle Hidden: o Defender marca esses
    return ["powershell", "-NoProfile", "-Command", SHORTCUT_SCRIPT]


def create_shortcut(root: Path) -> bool:
    """Cria o atalho na Área de Trabalho que aponta para iniciar.bat."""
    env = {**os.environ, "LV_TARGET": str(root / "iniciar.bat"), "LV_ROOT": str(root)}
    try:
        subprocess.run(shortcut_command(), env=env, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def close_handler(on_close: Callable[[], None], grace: float = CLOSE_GRACE) -> Callable[[int], bool]:
    """Trata o aviso de fechar a janela: para o laço principal e segura o processo enquanto a limpeza roda."""
    def handle(event: int) -> bool:
        if event != CTRL_CLOSE_EVENT:
            return False  # Ctrl+C e os outros avisos seguem o caminho normal do Python
        on_close()
        time.sleep(grace)  # sem a espera o Windows pode encerrar o processo antes do finally de run
        return True
    return handle


def install_close_handler(on_close: Callable[[], None]) -> None:
    """No Windows, fechar a janela pelo X chama on_close. No resto não faz nada."""
    global _close_routine
    if os.name != "nt":
        return
    _close_routine = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)(close_handler(on_close))
    ctypes.windll.kernel32.SetConsoleCtrlHandler(_close_routine, True)
