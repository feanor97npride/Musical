# Quebra de versos longos em linhas curtas de legenda: vírgula, conectivo e limite de palavras.
from engine.write_lyrics import MAX_WORDS, subtitle_lines


def test_virgula_perto_do_meio_vira_quebra():
    assert subtitle_lines("[Verse]\nEu caminhei por vales, sem ver a luz nenhuma vez") == (
        "[Verse]\nEu caminhei por vales,\nsem ver a luz nenhuma vez")


def test_verso_longo_quebra_em_linhas_curtas_sem_perder_palavras():
    lyrics = "[Verse]\nEu caminhei por vales sem ver a luz, carreguei no peito um peso\n\n[Chorus]\nVem comigo"
    result = subtitle_lines(lyrics).splitlines()
    assert result[0] == "[Verse]" and result[-2] == "[Chorus]"
    lines = [line for line in result if not line.startswith("[")]
    assert all(len(line.split()) <= MAX_WORDS for line in lines)
    assert [word for line in lines for word in line.split()] == (
        "Eu caminhei por vales sem ver a luz, carreguei no peito um peso Vem comigo".split())
