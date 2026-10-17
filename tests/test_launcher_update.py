# Testes da atualização: comandos registrados com um run falso, sem git, pip nem npm de verdade.
import subprocess
import sys
from types import SimpleNamespace

import pytest

from web.launcher import update


@pytest.fixture
def projeto(tmp_path, monkeypatch):
    (tmp_path / "renderer").mkdir()
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (tmp_path / "renderer" / "package-lock.json").write_text("{}\n", encoding="utf-8")
    # git e npm "existem" nos testes; quem roda de verdade é o run falso
    monkeypatch.setattr(update.shutil, "which", lambda nome: f"/usr/bin/{nome}")
    return tmp_path


def fake_run(root, novos_arquivos=None, codigo_pull=0, demora=False, codigo_outro=0):
    chamadas = []

    def run(args, **kwargs):
        chamadas.append(args)
        if "pull" in args:
            if demora:
                raise subprocess.TimeoutExpired(args, 60)
            for nome, texto in (novos_arquivos or {}).items():
                (root / nome).write_text(texto, encoding="utf-8")
            erro = "falha de rede" if codigo_pull else ""
            return SimpleNamespace(returncode=codigo_pull, stderr=erro)
        return SimpleNamespace(returncode=codigo_outro, stderr="")

    return run, chamadas


def test_sem_mudanca_so_faz_o_git_pull(projeto):
    run, chamadas = fake_run(projeto)
    update.update_project(projeto, run=run, log=lambda m: None)
    assert chamadas == [["/usr/bin/git", "pull", "--ff-only"]]


def test_requirements_mudou_roda_pip(projeto):
    run, chamadas = fake_run(projeto, novos_arquivos={"requirements.txt": "fastapi\nnovo\n"})
    update.update_project(projeto, run=run, log=lambda m: None)
    assert [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"] in chamadas


def test_lock_do_renderer_mudou_roda_npm_ci(projeto):
    run, chamadas = fake_run(projeto, novos_arquivos={"renderer/package-lock.json": '{"v": 2}\n'})
    update.update_project(projeto, run=run, log=lambda m: None)
    assert ["/usr/bin/npm", "ci"] in chamadas


def test_pull_com_erro_so_avisa(projeto):
    avisos = []
    run, chamadas = fake_run(projeto, codigo_pull=1)
    update.update_project(projeto, run=run, log=avisos.append)
    assert len(chamadas) == 1
    assert "não consegui atualizar" in avisos[0]


def test_pull_demorado_so_avisa(projeto):
    avisos = []
    run, _ = fake_run(projeto, demora=True)
    update.update_project(projeto, run=run, log=avisos.append)
    assert "demorou demais" in avisos[0]


def test_sem_git_so_avisa(projeto, monkeypatch):
    monkeypatch.setattr(update.shutil, "which", lambda nome: None)
    avisos = []
    run, chamadas = fake_run(projeto)
    update.update_project(projeto, run=run, log=avisos.append)
    assert chamadas == []
    assert "git não encontrado" in avisos[0]


def test_pip_que_falha_mostra_o_comando_manual(projeto):
    avisos = []
    run, _ = fake_run(projeto, novos_arquivos={"requirements.txt": "novo\n"}, codigo_outro=1)
    update.update_project(projeto, run=run, log=avisos.append)
    assert any("python -m pip install -r requirements.txt" in aviso for aviso in avisos)
