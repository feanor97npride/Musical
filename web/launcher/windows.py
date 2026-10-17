# Ações do Windows: encerrar a árvore de processos, copiar e criar o atalho.
import os
import signal
import subprocess
from pathlib import Path

SHORTCUT_SCRIPT = (
    "$d=[Environment]::GetFolderPath('Desktop');"
    "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Gerador de lyric video.lnk'));"
    "$s.TargetPath=$env:LV_TARGET;$s.WorkingDirectory=$env:LV_ROOT;"
    "$s.IconLocation='shell32.dll,13';$s.Save()"
)


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
