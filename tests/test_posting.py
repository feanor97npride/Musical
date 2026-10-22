# Testes das informações para postar: limites, formato das hashtags e texto do arquivo.
import pytest

from engine.posting import chapters, parts_text, posting_problems, posting_text, with_part

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


def test_espacos_nas_bordas_nao_contam_no_limite():
    assert posting_problems({**GOOD, "youtube_title": "x" * 100 + "\n"}) == []


def test_texto_para_postar_tem_um_rotulo_por_linha():
    text = posting_text({**GOOD, "title": "Manhã"})
    assert text.splitlines() == [
        "Título (YouTube): Manhã de fé",
        "Descrição (YouTube): Uma música de esperança.",
        "Legenda (TikTok): Depois da noite vem o sol",
        "Hashtags: #gospel #esperanca #louvor",
    ]


def test_capitulos_mudam_na_troca_de_secao_e_o_primeiro_comeca_em_zero():
    song = {"lines": [
        {"section": "verse", "start": 12.4}, {"section": "verse", "start": 20.0},
        {"section": "chorus", "start": 30.9}, {"section": "chorus", "start": 40.0},
        {"section": "verse", "start": 75.2}, {"section": "other", "start": 130.0},
    ]}
    assert chapters(song) == "00:00 Estrofe\n00:30 Refrão\n01:15 Estrofe\n02:10 Trecho"


def test_prefixo_da_parte_fica_inteiro_e_o_texto_e_cortado_no_limite():
    assert with_part("x" * 200, 2, 5, 150) == "Parte 2/5 · " + "x" * (150 - len("Parte 2/5 · "))
    assert with_part("Manhã", 1, 1, 150) == "Manhã"  # vídeo único não tem prefixo


def test_postar_txt_de_partes_com_textos_e_capitulos():
    song = {"lines": [{"section": "verse", "start": 0.0}, {"section": "chorus", "start": 30.0}]}
    text = parts_text(["01-a-parte-1-de-2.mp4", "02-a-parte-2-de-2.mp4"], song, GOOD)
    assert text.splitlines()[:5] == [
        "Arquivo: 01-a-parte-1-de-2.mp4",
        "Título: Parte 1/2 · Manhã de fé",
        "Legenda: Parte 1/2 · Depois da noite vem o sol",
        "Hashtags: #gospel #esperanca #louvor",
        "",
    ]
    assert text.endswith("Descrição do YouTube (com capítulos):\nUma música de esperança.\n\n00:00 Estrofe\n00:30 Refrão\n")


def test_postar_txt_sem_textos_traz_so_os_nomes_e_capitulos():
    song = {"lines": [{"section": "verse", "start": 0.0}]}
    assert parts_text(["a.mp4"], song, None) == "Arquivo: a.mp4\n\nDescrição do YouTube (com capítulos):\n00:00 Estrofe\n"
