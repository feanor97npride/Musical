# Testes da transcrição: como as palavras com tempo viram versos (o modelo em si não roda aqui).
from engine.transcribe import group_lines


def test_quebra_depois_de_pausa_longa():
    timed = [("oi", 0.0, 0.4), ("tudo", 0.5, 0.9), ("bem", 2.5, 2.9), ("sim", 3.0, 3.3)]
    assert group_lines(timed) == ["oi tudo", "bem sim"]


def test_quebra_depois_de_palavras_demais():
    timed = [(f"p{i}", i * 0.3, i * 0.3 + 0.2) for i in range(10)]
    assert group_lines(timed, max_words=8) == [" ".join(f"p{i}" for i in range(8)), "p8 p9"]


def test_ignora_palavra_vazia():
    assert group_lines([("", 0.0, 0.1), ("ola", 0.2, 0.4)]) == ["ola"]
