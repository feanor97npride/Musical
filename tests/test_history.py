# Histórico das letras com IA: guardar, listar, abrir e apagar, com o arquivo trocado por um de teste.
import json

import pytest

from web import history

DRAFT = {"title": "Manhã", "lyrics": "[Chorus]\num", "style": "acoustic pop", "youtube_title": "Manhã de fé",
         "youtube_description": "Uma música de esperança.", "tiktok_caption": "Depois da noite", "hashtags": ["#gospel"]}


@pytest.fixture(autouse=True)
def arquivo_de_teste(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY_FILE", tmp_path / "letras.json")
    return tmp_path / "letras.json"


def test_mais_recente_primeiro_e_lista_sem_a_letra():
    first = history.add("primeiro contexto", {**DRAFT, "title": "A"})
    second = history.add("segundo contexto", {**DRAFT, "title": "B"})
    assert [item["title"] for item in history.list_items()] == ["B", "A"]
    assert "lyrics" not in history.list_items()[0]
    assert history.get(first["id"])["context"] == "primeiro contexto"
    assert history.get(second["id"])["lyrics"] == DRAFT["lyrics"]


def test_apagar_remove_so_o_item_pedido():
    keep = history.add("fica", DRAFT)
    gone = history.add("some", DRAFT)
    assert history.remove(gone["id"]) is True
    assert history.remove(gone["id"]) is False
    assert [item["id"] for item in history.list_items()] == [keep["id"]]


def test_sem_arquivo_a_lista_e_vazia():
    assert history.list_items() == []
    assert history.get("qualquer") is None


def test_arquivo_corrompido_e_guardado_de_lado_e_nao_se_perde(arquivo_de_teste):
    arquivo_de_teste.write_text("{isto não é json", encoding="utf-8")
    assert history.list_items() == []
    assert (arquivo_de_teste.parent / "letras.corrompido.json").read_text(encoding="utf-8") == "{isto não é json"
    history.add("novo", DRAFT)  # continua funcionando depois do arquivo ruim
    assert len(history.list_items()) == 1


def test_gravacao_fica_no_arquivo_em_utf8(arquivo_de_teste):
    history.add("manhã de fé", DRAFT)
    saved = json.loads(arquivo_de_teste.read_text(encoding="utf-8"))
    assert saved[0]["context"] == "manhã de fé" and saved[0]["title"] == "Manhã"
