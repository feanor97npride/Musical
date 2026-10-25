# Os testes nunca ligam as automações do servidor, mesmo que o .env do PC as tenha ligado.
import pytest


@pytest.fixture(autouse=True)
def sem_automacoes(monkeypatch):
    for name in ("DRIVE_AUTO", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_NOTIFY"):
        monkeypatch.delenv(name, raising=False)
