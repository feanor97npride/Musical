# Testes das informações para postar: limites, formato das hashtags e texto do arquivo.
import pytest

from engine.posting import posting_problems, posting_text

GOOD = {
    "youtube_title": "Manhã de fé",
    "youtube_description": "Uma música de esperança.",
    "tiktok_caption": "Depois da noite vem o sol",
    "hashtags": ["#gospel", "#esperanca", "#louvor"],
}


def test_dados_validos_passam():
    assert posting_problems(GOOD) == []


@pytest.mark.parametrize("field, limit", [("youtube_title", 100), ("youtube_description", 1000), ("tiktok_caption", 150)])
def test_texto_no_limite_passa_e_acima_nao(field, limit):
    assert posting_problems({**GOOD, field: "x" * limit}) == []
    assert posting_problems({**GOOD, field: "x" * (limit + 1)}) == [f"{field} com mais de {limit} caracteres"]


@pytest.mark.parametrize("tags", [None, "#a #b #c", ["#a", "#b"], ["#a", "#b", "#c", "#d", "#e", "#f", "#g"],
                                  ["#a", "b", "#c"], ["#a", "# b", "#c"]])
def test_hashtags_fora_do_formato_sao_recusadas(tags):
    assert posting_problems({**GOOD, "hashtags": tags}) == [
        "hashtags fora do formato: de 3 a 6, cada uma com # e sem espaço"]


def test_texto_para_postar_tem_um_rotulo_por_linha():
    text = posting_text({**GOOD, "title": "Manhã"})
    assert text.splitlines() == [
        "Título (YouTube): Manhã de fé",
        "Descrição (YouTube): Uma música de esperança.",
        "Legenda (TikTok): Depois da noite vem o sol",
        "Hashtags: #gospel #esperanca #louvor",
    ]
