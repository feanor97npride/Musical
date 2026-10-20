# Testes da letra gerada: validação da resposta, retry, erros claros e CLI. A API nunca é chamada de verdade.
import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from engine import write_lyrics as module
from engine.lyrics import parse_lyrics
from engine.write_lyrics import MAX_CONTEXT, main, write_lyrics

LYRICS = "[Verse]\nAcordei com o sol na janela\nO café esfriando na mesa\n[Chorus]\nVem comigo\nVem comigo agora"
GOOD = {"title": "Manhã", "lyrics": LYRICS, "style": "acoustic pop, warm female vocals, 90 bpm"}
REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def good_json(**changes) -> str:
    return json.dumps({**GOOD, **changes}, ensure_ascii=False)


class FakeClient:
    """Responde com a sequência dada; uma exceção na lista é lançada no lugar da resposta."""

    def __init__(self, *replies, stop_reason="end_turn"):
        self.replies = list(replies)
        self.stop_reason = stop_reason
        self.calls = 0
        self.kwargs = {}
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        # igual à API real: um bloco "thinking" vem antes do bloco de texto
        thinking = SimpleNamespace(type="thinking", thinking="")
        return SimpleNamespace(stop_reason=self.stop_reason,
                               content=[thinking, SimpleNamespace(type="text", text=reply)])


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.delenv("THEME_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # sem isto, o .env do projeto repõe a chave e o teste chamaria a API de verdade
    monkeypatch.setattr(module, "load_dotenv", lambda *_args, **_kwargs: None)


def test_resposta_boa_vira_letra_que_o_parser_entende():
    client = FakeClient(good_json())
    draft = write_lyrics("uma música sobre a manhã", client=client)
    assert draft == GOOD
    assert {line["section"] for line in parse_lyrics(draft["lyrics"])} == {"verse", "chorus"}
    assert client.kwargs["output_config"]["format"]["type"] == "json_schema"  # JSON garantido pela API
    assert client.kwargs["output_config"]["effort"] == "medium"  # tempo cabe no túnel


def test_json_invalido_e_retentado():
    client = FakeClient("texto solto", good_json())
    assert write_lyrics("contexto", client=client)["title"] == "Manhã"
    assert client.calls == 2


def test_falha_de_conexao_e_retentada():
    client = FakeClient(anthropic.APIConnectionError(request=REQUEST), good_json())
    assert write_lyrics("contexto", client=client)["style"] == GOOD["style"]


def test_tempo_esgotado_e_retentado_com_motivo_claro():
    timeout = anthropic.APITimeoutError(request=REQUEST)
    client = FakeClient(timeout, anthropic.APITimeoutError(request=REQUEST))
    with pytest.raises(RuntimeError, match="demorou mais de 45 s"):
        write_lyrics("contexto", client=client)
    assert client.calls == 2


def test_erro_400_nao_tenta_de_novo_e_mostra_a_mensagem_da_api():
    response = httpx2.Response(400, request=REQUEST)
    error = anthropic.BadRequestError("Your credit balance is too low", response=response, body=None)
    client = FakeClient(error, good_json())
    with pytest.raises(RuntimeError, match="erro 400: Your credit balance is too low"):
        write_lyrics("contexto", client=client)
    assert client.calls == 1


def test_erro_529_tenta_de_novo():
    error = anthropic.APIStatusError("Overloaded", response=httpx2.Response(529, request=REQUEST), body=None)
    client = FakeClient(error, good_json())
    assert write_lyrics("contexto", client=client)["title"] == "Manhã"


def test_quebras_crlf_do_navegador_contam_como_uma():
    client = FakeClient(good_json())
    context = "\r\n".join(["x" * 99] * 40)  # 3999 caracteres com quebras LF; 4038 com CRLF, acima do limite
    assert write_lyrics(context, client=client)["title"] == "Manhã"
    assert "\r" not in client.kwargs["messages"][0]["content"]


def test_duas_falhas_dao_erro_com_o_motivo():
    client = FakeClient("não é json", "também não")
    with pytest.raises(RuntimeError, match="não veio em JSON"):
        write_lyrics("contexto", client=client)


def test_chave_recusada_nao_tenta_de_novo():
    error = anthropic.AuthenticationError("x", response=httpx2.Response(401, request=REQUEST), body=None)
    client = FakeClient(error, good_json())
    with pytest.raises(RuntimeError, match="confira o .env"):
        write_lyrics("contexto", client=client)
    assert client.calls == 1


def test_recusa_do_modelo_nao_tenta_de_novo():
    client = FakeClient(good_json(), good_json(), stop_reason="refusal")
    with pytest.raises(RuntimeError, match="recusou"):
        write_lyrics("contexto", client=client)
    assert client.calls == 1


def test_sem_chave_da_erro_claro(no_key):
    with pytest.raises(RuntimeError, match="THEME_API_KEY"):
        write_lyrics("contexto")


@pytest.mark.parametrize("context", ["   ", "x" * (MAX_CONTEXT + 1)])
def test_contexto_vazio_ou_longo_e_recusado_sem_chamar_a_api(context):
    client = FakeClient(good_json())
    with pytest.raises(ValueError):
        write_lyrics(context, client=client)
    assert client.calls == 0


@pytest.mark.parametrize("changes, motivo", [
    ({"lyrics": "[Verse]\num\ndois\ntrês\nquatro"}, "sem \\[Chorus\\]"),
    ({"lyrics": "[Chorus]\num\ndois"}, "menos de 4 versos"),
    ({"lyrics": LYRICS + "\n[Solo]\nlá lá lá"}, "marcador"),
    ({"style": "x" * 201}, "estilo"),
    ({"title": ""}, "campos vazios"),
])
def test_resposta_fora_do_formato_e_recusada(changes, motivo):
    client = FakeClient(good_json(**changes), good_json(**changes))
    with pytest.raises(RuntimeError, match=motivo):
        write_lyrics("contexto", client=client)


def test_cli_grava_letra_e_estilo_e_nao_sobrescreve(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(module, "write_lyrics", lambda context: GOOD)
    out = tmp_path / "samples" / "manha.txt"
    assert main(["--context", "manhã", "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == LYRICS + "\n"
    assert (tmp_path / "samples" / "manha.estilo.txt").read_text(encoding="utf-8") == GOOD["style"] + "\n"
    assert "acoustic pop" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["--context", "manhã", "--out", str(out)])
    assert main(["--context", "manhã", "--out", str(out), "--force"]) == 0


def test_cli_le_o_contexto_de_arquivo(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(module, "write_lyrics", lambda context: seen.append(context) or GOOD)
    context_file = tmp_path / "contexto.txt"
    context_file.write_text("uma música sobre o mar", encoding="utf-8")
    assert main(["--context-file", str(context_file), "--out", str(tmp_path / "mar.txt")]) == 0
    assert seen == ["uma música sobre o mar"]


def test_cli_mostra_erro_sem_traceback(tmp_path, monkeypatch, capsys):
    def failing(_context):
        raise RuntimeError("falta THEME_API_KEY no .env para gerar a letra")

    monkeypatch.setattr(module, "write_lyrics", failing)
    out = tmp_path / "x.txt"
    assert main(["--context", "c", "--out", str(out)]) == 1
    assert "THEME_API_KEY" in capsys.readouterr().err
    assert not out.exists()
