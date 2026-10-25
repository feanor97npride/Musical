# Aviso no Telegram: uma mensagem pelo bot do usuário (TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env).
import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)
TIMEOUT = 10  # segundos; o aviso não pode prender a thread
MAX_TEXT = 4000  # o Telegram recusa mensagens com mais de 4096 caracteres


def _settings() -> tuple[str, str]:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def configured() -> bool:
    return all(_settings())


def send(text: str) -> None:
    """Manda a mensagem. Qualquer falha vai só para o log, sem o token: um aviso nunca derruba um job."""
    token, chat = _settings()
    if not token or not chat:
        return
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat, "text": text[:MAX_TEXT]}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(request, timeout=TIMEOUT).close()
    except urllib.error.HTTPError as error:  # token ou chat errado: o código diz qual
        logger.warning("o Telegram recusou o aviso (código %s)", error.code)
    except (urllib.error.URLError, OSError):
        logger.warning("não consegui falar com o Telegram")
