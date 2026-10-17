# Atualiza o projeto antes de ligar: git pull e, só se algo mudou, pip e npm.
import hashlib
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

WATCHED = ["requirements.txt", "renderer/package-lock.json"]


def file_digest(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest() if path.exists() else ""


def digests(root: Path) -> dict[str, str]:
    return {name: file_digest(root / name) for name in WATCHED}


def update_project(root: Path, run: Callable = subprocess.run,
                   log: Callable[[str], None] = print) -> None:
    before = digests(root)
    git = shutil.which("git")
    if git is None:
        log("git não encontrado; seguindo sem atualizar")
        return
    try:
        result = run([git, "pull", "--ff-only"], cwd=root, stdin=subprocess.DEVNULL,
                     capture_output=True, text=True, timeout=60,
                     env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except subprocess.TimeoutExpired:
        log("aviso: a atualização demorou demais; seguindo com a versão atual")
        return
    if result.returncode != 0:
        log("aviso: não consegui atualizar (" + result.stderr.strip() + "); seguindo com a versão atual")
        return
    after = digests(root)
    if after["requirements.txt"] != before["requirements.txt"]:
        log("dependências Python mudaram; instalando...")
        code = run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=root).returncode
        if code != 0:  # a próxima execução não vê mudança, então o comando manual precisa aparecer aqui
            log("aviso: a instalação falhou; rode à mão: python -m pip install -r requirements.txt")
    if after["renderer/package-lock.json"] != before["renderer/package-lock.json"]:
        npm = shutil.which("npm")
        if npm is None:
            log("npm não encontrado; rode npm ci dentro de renderer/ à mão")
            return
        log("dependências do renderer mudaram; instalando...")
        code = run([npm, "ci"], cwd=root / "renderer").returncode
        if code != 0:
            log("aviso: npm ci falhou; rode à mão: npm ci (dentro de renderer/)")
