# Pós-processamento dos tempos do alinhador: monotônicos, dentro do áudio, derivados das palavras.
from engine.schema import Line, Word

MIN_LINE = 0.01  # shortcut: duração mínima de verso que o alinhador zerou; subir se a legenda piscar


def fix_words(raw: list[tuple[str, float, float]], duration: float) -> list[Word]:
    """Deixa os starts não decrescentes, os ends >= start e tudo entre 0 e a duração."""
    words: list[Word] = []
    previous = 0.0
    for text, start, end in raw:
        start = min(max(start, previous), duration)
        end = min(max(end, start), duration)
        words.append(Word(text, start, end))
        previous = start
    return words


def split_by_counts(items: list, counts: list[int]) -> list[list]:
    """Distribui itens em sequência entre os versos, pelo número de palavras de cada um."""
    groups, index = [], 0
    for count in counts:
        groups.append(items[index:index + count])
        index += count
    return groups


def build_lines(lyrics: list[dict], groups: list[list[tuple[str, float, float]]], duration: float) -> list[Line]:
    """Monta as linhas do song.json. Start e end do verso vêm das palavras dele."""
    fixed = fix_words([item for group in groups for item in group], duration)
    lines: list[Line] = []
    index = 0
    for number, (verse, group) in enumerate(zip(lyrics, groups)):
        words = fixed[index:index + len(group)]
        index += len(group)
        if not words:
            raise ValueError(f"o alinhador não devolveu palavras para o verso {number}: {verse['text']!r}")
        start, end = words[0].start, words[-1].end
        if end <= start:
            end = min(start + MIN_LINE, duration)
            words[-1].end = end
        lines.append(Line(number, verse["text"], verse["section"], start, end, words))
    return lines
