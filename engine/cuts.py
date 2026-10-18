# Cortes para TikTok e Kwai: versos inteiros juntados até chegar perto do alvo, com folga nas pontas.
import math

LEAD = 0.5  # segundos de folga antes do primeiro verso e depois do último


def plan_cuts(song: dict, target: float = 30.0) -> list[tuple[float, float]]:
    """Divide as linhas do song.json em cortes de cerca de `target` segundos, sem cortar verso no meio."""
    groups: list[list[dict]] = []
    for line in song["lines"]:
        if groups and line["end"] - groups[-1][0]["start"] <= target:
            groups[-1].append(line)
        else:
            # shortcut: verso maior que o alvo vira um corte maior que ele, subir se incomodar
            groups.append([line])
    if len(groups) > 1 and groups[-1][-1]["end"] - groups[-1][0]["start"] < target / 2:
        groups[-2].extend(groups.pop())  # último corte curto demais: junta com o anterior
    duration = song["audio"]["duration"]
    # floor, não round: arredondar o fim para cima passaria da duração e o clip seria recusado
    return [
        (math.floor(max(0.0, group[0]["start"] - LEAD) * 100) / 100,
         math.floor(min(duration, group[-1]["end"] + LEAD) * 100) / 100)
        for group in groups
    ]
