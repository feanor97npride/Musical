# Ponto de entrada: python -m web.launcher. Liga o servidor e o túnel e abre o site.
import argparse
import sys
import threading
import time
import webbrowser
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import quote

from dotenv import dotenv_values

from web.launcher.checks import Plan, preflight
from web.launcher.services import RestartPolicy, Service, extract_tunnel_url
from web.launcher.update import update_project
from web.launcher.windows import copy_to_clipboard, create_shortcut, install_close_handler

ROOT = Path(__file__).resolve().parents[2]
TUNNEL_READY = "Registered tunnel connection"  # linha que o cloudflared escreve quando a conexão registra


def site_link(site_url: str, tunnel_url: str) -> str:
    return f"{site_url}/#server={quote(tunnel_url, safe='')}"


def announce_tunnel(url: str, site_url: str, log: Callable[[str], None],
                    open_link: Callable[[str], object], copy: Callable[[str], bool]) -> None:
    log(f"endereço do túnel: {url}")
    if copy(url):  # só a URL do túnel; a senha nunca sai daqui
        log("endereço copiado para a área de transferência")
    if not site_url:
        log("SITE_URL não definido: abra o site e cole o endereço acima")
        return
    link = site_link(site_url, url)
    log(f"abrindo o site: {link}")
    open_link(link)


def tunnel_address(tunnel_host: str, linha: str) -> str | None:
    if tunnel_host:  # túnel fixo: o endereço já é conhecido, falta só a conexão
        return f"https://{tunnel_host}" if TUNNEL_READY in linha else None
    return extract_tunnel_url(linha)


def service_env(nome: str, env: Mapping[str, str]) -> dict[str, str]:
    # só o túnel recebe o token; o servidor não precisa dele
    if nome == "túnel":
        return {**env, "NO_AUTOUPDATE": "1"}
    return {chave: valor for chave, valor in env.items() if chave != "TUNNEL_TOKEN"}


def default_commands(plan: Plan) -> dict[str, list[str]]:
    commands = {"servidor": [sys.executable, "-m", "uvicorn", "web.app:app",
                             "--host", "127.0.0.1", "--port", str(plan.port), "--no-access-log"]}
    if plan.cloudflared and plan.tunnel_host:  # o destino do túnel fixo fica no painel da Cloudflare
        commands["túnel"] = [plan.cloudflared, "tunnel", "run"]
    elif plan.cloudflared:
        commands["túnel"] = [plan.cloudflared, "tunnel", "--no-autoupdate",
                             "--url", f"http://127.0.0.1:{plan.port}"]
    return commands


def run(plan: Plan, root: Path, env: Mapping[str, str], stop: threading.Event,
        open_link: Callable[[str], object] = webbrowser.open,
        copy: Callable[[str], bool] = copy_to_clipboard,
        sleep: Callable[[float], None] = time.sleep,
        commands: dict[str, list[str]] | None = None) -> int:
    lock = threading.Lock()
    ultima = {"url": ""}

    def log(texto: str) -> None:
        with lock:  # linhas de processos diferentes não podem se misturar
            print(texto, flush=True)

    def on_line(nome: str, linha: str) -> None:
        log(f"[{nome}] {linha}")
        if nome == "túnel":
            url = tunnel_address(plan.tunnel_host, linha)
            if url and url != ultima["url"]:
                ultima["url"] = url
                announce_tunnel(url, plan.site_url, log, open_link, copy)

    comandos = commands or default_commands(plan)
    servicos = [Service(nome, argv, root, service_env(nome, env), on_line) for nome, argv in comandos.items()]
    politicas = {servico.name: RestartPolicy() for servico in servicos}
    try:
        for servico in servicos:
            servico.start()
        while not stop.is_set():
            sleep(1)
            for servico in servicos:
                if servico.running() or stop.is_set():
                    continue
                if not politicas[servico.name].allow():
                    log(f"[{servico.name}] caiu muitas vezes seguidas; desisti")
                    return 1
                log(f"[{servico.name}] parou; reiniciando em 3 s...")
                sleep(3)
                servico.start()
        return 0
    finally:
        for servico in servicos:  # nada pode ficar aberto depois de sair
            servico.stop()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m web.launcher",
                                     description="Liga o servidor e o túnel e abre o site")
    parser.add_argument("--criar-atalho", action="store_true", help="cria o atalho na Área de Trabalho")
    parser.add_argument("--sem-atualizar", action="store_true", help="não faz git pull antes de ligar")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.criar_atalho:
        ok = create_shortcut(ROOT)
        print("atalho criado na Área de Trabalho" if ok else "não consegui criar o atalho", flush=True)
        return 0 if ok else 1
    env = {chave: valor for chave, valor in dotenv_values(ROOT / ".env").items() if valor is not None}
    plan = preflight(env)
    for aviso in plan.warnings:
        print(f"aviso: {aviso}", flush=True)
    if plan.abort:
        print(f"erro: {plan.abort}", flush=True)
        return 1
    if not args.sem_atualizar:
        update_project(ROOT)
    stop = threading.Event()
    install_close_handler(stop.set)  # fechar a janela pelo X também encerra o servidor e o túnel
    try:
        return run(plan, ROOT, env, stop)
    except KeyboardInterrupt:
        stop.set()
        return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
