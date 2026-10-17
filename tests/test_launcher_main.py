# Testes do ponto de entrada: link do site, anúncio do túnel e o fluxo com processos de exemplo.
import sys
import threading
import time

from web.launcher import __main__ as launcher
from web.launcher.checks import Plan

LINHA_ABC = "|  https://abc-def.trycloudflare.com  |"
SERVIDOR_PARADO = [sys.executable, "-c", "import time; time.sleep(30)"]


def test_link_do_site_leva_o_endereco_do_tunel_codificado():
    link = launcher.site_link("https://site.vercel.app", "https://abc-def.trycloudflare.com")
    assert link == "https://site.vercel.app/#server=https%3A%2F%2Fabc-def.trycloudflare.com"


def test_anuncio_copia_so_o_tunel_e_abre_o_site():
    linhas, abertos, copiados = [], [], []
    launcher.announce_tunnel("https://abc-def.trycloudflare.com", "https://site.vercel.app",
                             linhas.append, abertos.append, lambda texto: copiados.append(texto) or True)
    assert copiados == ["https://abc-def.trycloudflare.com"]
    assert abertos == ["https://site.vercel.app/#server=https%3A%2F%2Fabc-def.trycloudflare.com"]


def test_sem_site_url_nao_abre_o_navegador():
    linhas, abertos = [], []
    launcher.announce_tunnel("https://abc-def.trycloudflare.com", "", linhas.append,
                             abertos.append, lambda texto: True)
    assert abertos == []
    assert any("SITE_URL não definido" in linha for linha in linhas)


def test_fluxo_anuncia_o_tunel_e_abre_o_site(tmp_path):
    abertos, copiados = [], []
    stop = threading.Event()
    chamadas = []

    def sleep(_segundos):
        chamadas.append(1)
        time.sleep(0.05)
        if abertos or len(chamadas) > 200:  # 200 voltas é o limite de segurança (10 s)
            stop.set()

    comandos = {
        "servidor": SERVIDOR_PARADO,
        "túnel": [sys.executable, "-c", f"import time; print({LINHA_ABC!r}, flush=True); time.sleep(30)"],
    }
    plano = Plan(port=8123, site_url="https://site.vercel.app", cloudflared="cloudflared")
    codigo = launcher.run(plano, tmp_path, {}, stop, open_link=abertos.append,
                          copy=lambda texto: copiados.append(texto) or True, sleep=sleep, commands=comandos)
    assert codigo == 0
    assert len(abertos) == 1
    assert copiados == ["https://abc-def.trycloudflare.com"]


def test_tunel_que_cai_volta_com_endereco_novo(tmp_path):
    contador = tmp_path / "contador.txt"
    script = (
        "import pathlib, time\n"
        f"c = pathlib.Path({str(contador)!r})\n"
        "n = int(c.read_text()) if c.exists() else 0\n"
        "c.write_text(str(n + 1))\n"
        "print('|  https://abc-def.trycloudflare.com  |' if n == 0 else '|  https://xyz-uvw.trycloudflare.com  |', flush=True)\n"
        "time.sleep(0.2 if n == 0 else 30)\n"
    )
    abertos = []
    stop = threading.Event()
    chamadas = []

    def sleep(_segundos):
        chamadas.append(1)
        time.sleep(0.05)
        if len(abertos) >= 2 or len(chamadas) > 300:
            stop.set()

    comandos = {"servidor": SERVIDOR_PARADO, "túnel": [sys.executable, "-c", script]}
    plano = Plan(port=8123, site_url="https://site.vercel.app", cloudflared="cloudflared")
    launcher.run(plano, tmp_path, {}, stop, open_link=abertos.append, copy=lambda texto: True,
                 sleep=sleep, commands=comandos)
    assert len(abertos) == 2
    assert "abc-def" in abertos[0]
    assert "xyz-uvw" in abertos[1]


def test_parse_args_padroes():
    args = launcher.parse_args([])
    assert args.criar_atalho is False
    assert args.sem_atualizar is False


def test_criar_atalho_chama_o_criador(monkeypatch):
    monkeypatch.setattr(launcher, "create_shortcut", lambda root: True)
    assert launcher.main(["--criar-atalho"]) == 0
