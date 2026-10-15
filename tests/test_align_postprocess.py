# Testes do pós-processamento dos tempos com dados falsos, sem carregar modelo.
import pytest

from engine.postprocess import MIN_LINE, build_lines, fix_words, split_by_counts
from engine.schema import Audio, Song, validate_song


def test_tempos_fora_de_ordem_ficam_nao_decrescentes():
    words = fix_words([("a", 1.0, 1.2), ("b", 0.5, 0.9), ("c", 2.0, 2.4)], duration=10.0)
    assert [w.start for w in words] == [1.0, 1.0, 2.0]
    assert all(w.end >= w.start for w in words)


def test_tempos_limitados_a_duracao_do_audio():
    words = fix_words([("a", 4.0, 6.0), ("b", 7.0, 9.0)], duration=5.0)
    assert [(w.start, w.end) for w in words] == [(4.0, 5.0), (5.0, 5.0)]


def test_split_by_counts_distribui_em_sequencia():
    assert split_by_counts(["a", "b", "c"], [2, 1]) == [["a", "b"], ["c"]]


def test_inicio_e_fim_do_verso_vem_das_palavras():
    lyrics = [{"text": "um dois", "section": "verse"}, {"text": "três", "section": "chorus"}]
    groups = [[("um", 1.0, 1.4), ("dois", 1.4, 2.0)], [("três", 2.5, 3.5)]]
    lines = build_lines(lyrics, groups, duration=10.0)
    assert [(line.id, line.start, line.end) for line in lines] == [(0, 1.0, 2.0), (1, 2.5, 3.5)]
    assert lines[1].section == "chorus"


def test_resultado_passa_no_validate_song():
    lyrics = [{"text": "um dois", "section": "verse"}, {"text": "três", "section": "chorus"}]
    groups = [[("um", 1.0, 1.4), ("dois", 1.4, 2.0)], [("três", 2.5, 3.5)]]
    lines = build_lines(lyrics, groups, duration=10.0)
    song = Song(language="pt", audio=Audio("musica.mp3", 10.0, 96.0), lines=lines)
    assert validate_song(song.to_dict()) == []


def test_verso_de_duracao_zero_ganha_fim_minimo():
    lyrics = [{"text": "oi", "section": "verse"}]
    lines = build_lines(lyrics, [[("oi", 1.0, 1.0)]], duration=10.0)
    assert lines[0].end == pytest.approx(1.0 + MIN_LINE)
    song = Song(language="pt", audio=Audio("musica.mp3", 10.0, 96.0), lines=lines)
    assert validate_song(song.to_dict()) == []


def test_verso_sem_palavras_gera_erro_claro():
    lyrics = [{"text": "um", "section": "verse"}, {"text": "dois", "section": "verse"}]
    with pytest.raises(ValueError, match="verso 1"):
        build_lines(lyrics, [[("um", 1.0, 1.5)], []], duration=10.0)
