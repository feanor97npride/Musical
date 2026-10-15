# Testes da agrupagem de palavras por verso em align.py, com resultado falso e sem modelo.
from types import SimpleNamespace

from engine.align import _groups


def word(text: str, start: float, end: float) -> SimpleNamespace:
    return SimpleNamespace(word=text, start=start, end=end)


def test_usa_os_segmentos_quando_batem_com_os_versos():
    lyrics = [{"text": "um dois"}, {"text": "três"}]
    result = SimpleNamespace(segments=[
        SimpleNamespace(words=[word("um", 1.0, 1.4), word("dois", 1.4, 2.0)]),
        SimpleNamespace(words=[word("três", 2.5, 3.5)]),
    ])
    assert _groups(result, lyrics) == [[("um", 1.0, 1.4), ("dois", 1.4, 2.0)], [("três", 2.5, 3.5)]]


def test_sem_correspondencia_distribui_pela_contagem_de_palavras():
    lyrics = [{"text": "um dois"}, {"text": "três"}]
    flat = [word("um", 1.0, 1.4), word("dois", 1.4, 2.0), word("três", 2.5, 3.5)]
    result = SimpleNamespace(
        segments=[SimpleNamespace(words=flat)],
        all_words=lambda: flat,
    )
    assert _groups(result, lyrics) == [[("um", 1.0, 1.4), ("dois", 1.4, 2.0)], [("três", 2.5, 3.5)]]
