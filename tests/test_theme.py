# Testes do tema: validação da resposta, retry, fallback e ausência de chave. A API nunca é chamada de verdade.
import json
from types import SimpleNamespace

import pytest

from engine.checks import check_theme
from engine.theme import analyze_theme, default_theme

GOOD = {
    "title": "Saudade no fim da tarde",
    "mood": "melancólico",
    "keywords": ["saudade", "estrada", "pôr do sol"],
    "palette": ["#1B1B3A", "#693668", "#A74482"],
    "font": "Playfair Display",
    "visual_concept": "Gradiente lento em tons de crepúsculo",
}


def good_json(**changes) -> str:
    return json.dumps({**GOOD, **changes}, ensure_ascii=False)


class FakeClient:
    """Responde com a sequência dada; uma exceção na lista é lançada no lugar da resposta."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **_kwargs):
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        # igual à API real: um bloco "thinking" vem antes do bloco de texto
        thinking = SimpleNamespace(type="thinking", thinking="...")
        return SimpleNamespace(content=[thinking, SimpleNamespace(type="text", text=reply)])


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # sem isto, o .env do projeto repõe a chave e o teste chamaria a API de verdade
    monkeypatch.setattr("engine.theme.load_dotenv", lambda *_args, **_kwargs: None)


def test_default_theme_passa_na_validacao_do_tema():
    errors: list[str] = []
    check_theme(default_theme().to_dict(), errors)
    assert errors == []


def test_sem_chave_devolve_padrao(no_key):
    assert analyze_theme("letra") == default_theme()


def test_resposta_valida_com_cercas_de_codigo():
    client = FakeClient("```json\n" + good_json() + "\n```")
    theme = analyze_theme("letra", client=client)
    assert theme.palette == GOOD["palette"]
    assert client.calls == 1


def test_falha_na_primeira_tentativa_e_sucesso_na_segunda():
    client = FakeClient("texto solto, sem JSON", good_json())
    assert analyze_theme("letra", client=client).font == "Playfair Display"
    assert client.calls == 2


def test_duas_falhas_usam_tema_padrao():
    client = FakeClient("não é json", good_json(palette=["#FFF", "#000", "#888"]))
    assert analyze_theme("letra", client=client) == default_theme()
    assert client.calls == 2


def test_cor_fora_do_formato_rrggbb_e_recusada():
    client = FakeClient(good_json(palette=["#FFF", "#000", "#888"]), good_json(palette=["#FFF", "#000", "#888"]))
    assert analyze_theme("letra", client=client) == default_theme()


def test_fonte_fora_da_lista_e_recusada():
    client = FakeClient(good_json(font="Arial"), good_json(font="Arial"))
    assert analyze_theme("letra", client=client) == default_theme()


def test_fonte_nao_texto_nao_derruba_a_pipeline():
    client = FakeClient(good_json(font=["Inter"]), good_json(font=["Inter"]))
    assert analyze_theme("letra", client=client) == default_theme()


def test_excecao_da_api_e_retentada():
    client = FakeClient(RuntimeError("rede caiu"), good_json())
    assert analyze_theme("letra", client=client).mood == "melancólico"
    assert client.calls == 2


def test_duas_excecoes_usam_tema_padrao():
    client = FakeClient(RuntimeError("a"), RuntimeError("b"))
    assert analyze_theme("letra", client=client) == default_theme()
