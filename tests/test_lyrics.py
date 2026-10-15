# Testes do parser da letra: marcadores de seção, linhas em branco e texto plano.
from engine.lyrics import flat_text, parse_lyrics


def test_letra_sem_marcadores_vira_verso():
    assert parse_lyrics("Primeira linha\nSegunda linha\n") == [
        {"text": "Primeira linha", "section": "verse"},
        {"text": "Segunda linha", "section": "verse"},
    ]


def test_marcadores_em_portugues_e_ingles():
    text = "[Intro]\nAbre\n[Refrão]\nCoro\n[Verse]\nVerso\n[Ponte]\nMeio\n[Chorus]\nCoro dois\n[Bridge]\nPonte\n[Outro]\nFim"
    assert [line["section"] for line in parse_lyrics(text)] == [
        "intro", "chorus", "verse", "bridge", "chorus", "bridge", "outro",
    ]


def test_marcador_desconhecido_vira_other():
    assert parse_lyrics("[Solo]\nNota") == [{"text": "Nota", "section": "other"}]


def test_secao_continua_ate_o_proximo_marcador():
    lines = parse_lyrics("[Refrão]\nUm\nDois\n[Verso]\nTrês")
    assert [line["section"] for line in lines] == ["chorus", "chorus", "verse"]


def test_marcador_nunca_entra_no_texto_mas_colchetes_no_meio_ficam():
    lines = parse_lyrics("[Refrão]\nEle [sorri] alto")
    assert lines == [{"text": "Ele [sorri] alto", "section": "chorus"}]


def test_linhas_em_branco_duplicadas_sao_ignoradas():
    assert [line["text"] for line in parse_lyrics("\n\nA\n\n\n\nB\n   \n")] == ["A", "B"]


def test_acentos_e_marcador_em_maiusculas():
    assert parse_lyrics("[REFRÃO]\nSão Paulo, coração\n") == [
        {"text": "São Paulo, coração", "section": "chorus"},
    ]


def test_bom_no_inicio_nao_estraga_o_primeiro_marcador():
    assert parse_lyrics("﻿[Intro]\nOi") == [{"text": "Oi", "section": "intro"}]


def test_flat_text_junta_versos_com_quebra_de_linha():
    assert flat_text(parse_lyrics("[Refrão]\nUm\n\nDois")) == "Um\nDois"
