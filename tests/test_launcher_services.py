# Testes dos serviços do iniciador: URL do túnel, limite de reinícios e processos de verdade (stubs Python).
import os
import sys
import time
from pathlib import Path

import pytest

from web.launcher.services import RestartPolicy, Service, child_env, extract_tunnel_url


def test_acha_a_url_do_tunel_em_linha_com_ruido():
    linha = "2026-10-17 INF |  https://ABC-def.trycloudflare.com  |"
    assert extract_tunnel_url(linha) == "https://abc-def.trycloudflare.com"


def test_ignora_o_endereco_api_das_mensagens_de_erro():
    assert extract_tunnel_url("erro ao falar com https://api.trycloudflare.com") is None


def test_linha_sem_url_devolve_none():
    assert extract_tunnel_url("iniciando o túnel...") is None


def test_limite_de_reinicios_e_liberado_depois_da_janela():
    agora = [0.0]
    politica = RestartPolicy(limit=5, window=60.0, clock=lambda: agora[0])
    assert all(politica.allow() for _ in range(5))
    assert politica.allow() is False  # o sexto pedido dentro da janela é negado
    agora[0] = 61.0
    assert politica.allow() is True  # passou a janela, libera de novo


def rodar(argv: list[str], pasta: Path) -> list[tuple[str, str]]:
    recebido = []
    servico = Service("teste", argv, pasta, {}, lambda nome, linha: recebido.append((nome, linha)))
    servico.start()
    prazo = time.monotonic() + 10
    while servico.running() and time.monotonic() < prazo:  # espera o processo acabar sozinho
        time.sleep(0.05)
    servico.stop()  # a leitura termina junto, então a saída já está toda no callback
    return recebido


def test_linha_da_saida_chega_ao_callback(tmp_path):
    assert rodar([sys.executable, "-c", "print('ola')"], tmp_path) == [("teste", "ola")]


def test_bytes_invalidos_nao_derrubam_a_leitura(tmp_path):
    codigo = "import sys; sys.stdout.buffer.write(b'\\xff\\n'); print('depois')"
    assert ("teste", "depois") in rodar([sys.executable, "-c", codigo], tmp_path)


def test_ambiente_do_filho_usa_utf8():
    assert child_env({})["PYTHONIOENCODING"] == "utf-8"
    assert child_env({})["PYTHONUTF8"] == "1"


def vivo(pid: int) -> bool:
    # no Linux, um processo morto e ainda não colhido aparece com estado 'Z'
    estado = Path(f"/proc/{pid}/stat")
    if not estado.exists():
        return False
    return estado.read_text().split(")")[-1].split()[0] != "Z"


@pytest.mark.skipif(os.name == "nt", reason="teste de processos do Linux")
def test_stop_mata_tambem_o_neto(tmp_path):
    codigo = ("import subprocess, sys, time; "
              "neto = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
              "print(neto.pid, flush=True); time.sleep(60)")
    saida = []
    servico = Service("teste", [sys.executable, "-c", codigo], tmp_path, {}, lambda _nome, linha: saida.append(linha))
    servico.start()
    prazo = time.monotonic() + 10
    while not saida and time.monotonic() < prazo:
        time.sleep(0.05)
    neto = int(saida[0])
    servico.stop()
    assert not vivo(neto)
