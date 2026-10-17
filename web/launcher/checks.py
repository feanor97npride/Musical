# Verificações antes de ligar: endereços, senha, porta e cloudflared.
import os
import shutil
import socket
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

DEFAULT_PORT = 8000
WINDOWS_PATHS = [
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
    r"C:\Program Files\cloudflared\cloudflared.exe",
]


def normalize_origin(value: str) -> str:
    """'https://Site.vercel.app/x/' vira 'https://site.vercel.app'; valor inválido vira ''."""
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return ""
    return f"{parts.scheme}://{parts.netloc}".lower()


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def find_cloudflared(env: Mapping[str, str]) -> str | None:
    # CLOUDFLARED_BIN serve para testes e para instalações fora do padrão
    found = env.get("CLOUDFLARED_BIN") or shutil.which("cloudflared")
    return found or next((path for path in WINDOWS_PATHS if os.path.exists(path)), None)


@dataclass
class Plan:
    port: int
    site_url: str  # vazio = não abrir o navegador
    cloudflared: str | None  # None = só local, sem túnel
    warnings: list[str] = field(default_factory=list)
    abort: str = ""  # texto do erro; vazio = pode seguir
    tunnel_host: str = ""  # endereço fixo do túnel com token; vazio = túnel aleatório


def preflight(env: Mapping[str, str], in_use: Callable[[int], bool] = port_in_use,
              finder: Callable[[Mapping[str, str]], str | None] = find_cloudflared) -> Plan:
    try:
        port = int(env.get("PORT") or DEFAULT_PORT)
    except ValueError:
        return Plan(DEFAULT_PORT, "", None, abort="PORT no .env precisa ser um número")
    site = normalize_origin(env.get("SITE_URL", ""))
    allowed = {normalize_origin(item) for item in env.get("ALLOWED_ORIGINS", "").split(",")}
    plan = Plan(port, site, finder(env))
    if in_use(port):
        plan.abort = f"a porta {port} já está em uso; feche o outro programa e tente de novo"
    token = env.get("TUNNEL_TOKEN", "").strip()
    host = env.get("TUNNEL_HOSTNAME", "").strip().lower()
    if token and not host:
        plan.abort = plan.abort or "TUNNEL_TOKEN precisa de TUNNEL_HOSTNAME no .env (o endereço fixo do túnel)"
    elif token:
        plan.tunnel_host = host
    elif host:
        plan.warnings.append("TUNNEL_HOSTNAME sem TUNNEL_TOKEN: ignorado; o túnel usa endereço aleatório")
    if not site:
        plan.warnings.append("SITE_URL vazio ou inválido: o navegador não será aberto")
    elif site not in allowed:
        plan.warnings.append("SITE_URL não está em ALLOWED_ORIGINS: o navegador vai bloquear o site")
    if plan.cloudflared is None:
        plan.warnings.append("cloudflared não encontrado (winget install --id Cloudflare.cloudflared): só local")
    elif not env.get("ACCESS_TOKEN", "").strip():
        plan.warnings.append("ACCESS_TOKEN vazio: o túnel NÃO será aberto (qualquer um usaria seu computador)")
        plan.cloudflared = None
    if not env.get("THEME_API_KEY", "").strip():
        plan.warnings.append("THEME_API_KEY vazio: o fundo vai usar o tema padrão")
    return plan
