# Testes do aviso no Telegram: a requisição certa, e falha de rede ou de token nunca levanta nem mostra o token.
import json
import urllib.error

from web import telegram


class Resposta:
    def close(self) -> None:
        pass


def configurar(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:SEGREDO")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")


def test_sem_token_ou_sem_chat_nao_esta_configurado(monkeypatch):
    assert not telegram.configured()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:SEGREDO")
    assert not telegram.configured()  # falta o chat
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    assert telegram.configured()


def test_sem_configuracao_nao_faz_pedido(monkeypatch):
    monkeypatch.setattr(telegram.urllib.request, "urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("não devia chamar")))
    telegram.send("oi")


def test_envia_pela_api_do_bot_com_chat_e_texto(monkeypatch):
    configurar(monkeypatch)
    pedidos = []
    monkeypatch.setattr(telegram.urllib.request, "urlopen", lambda req, timeout: pedidos.append((req, timeout)) or Resposta())
    telegram.send("Vídeo pronto")
    request, timeout = pedidos[0]
    assert request.full_url == "https://api.telegram.org/bot123:SEGREDO/sendMessage"
    assert json.loads(request.data) == {"chat_id": "42", "text": "Vídeo pronto"}
    assert timeout == telegram.TIMEOUT


def test_texto_muito_longo_e_cortado(monkeypatch):
    configurar(monkeypatch)
    pedidos = []
    monkeypatch.setattr(telegram.urllib.request, "urlopen", lambda req, timeout: pedidos.append(req) or Resposta())
    telegram.send("a" * 5000)
    assert len(json.loads(pedidos[0].data)["text"]) == telegram.MAX_TEXT


def test_erro_de_rede_nao_levanta_e_o_log_nao_tem_o_token(monkeypatch, caplog):
    configurar(monkeypatch)

    def sem_rede(request, timeout):
        raise urllib.error.URLError("sem rede")

    monkeypatch.setattr(telegram.urllib.request, "urlopen", sem_rede)
    telegram.send("oi")  # não pode levantar
    assert "Telegram" in caplog.text
    assert "SEGREDO" not in caplog.text


def test_token_errado_loga_so_o_codigo(monkeypatch, caplog):
    configurar(monkeypatch)

    def recusa(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(telegram.urllib.request, "urlopen", recusa)
    telegram.send("oi")
    assert "401" in caplog.text
    assert "SEGREDO" not in caplog.text
