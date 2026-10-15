# Regras de validação do song.json, usadas por validate_song() em schema.py.
import math
import re

SECTIONS = {"intro", "verse", "chorus", "bridge", "outro", "other"}
FONTS = {"Inter", "Bebas Neue", "Playfair Display", "Poppins", "Montserrat"}
HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")
END_TOLERANCE = 0.05  # segundos de folga no fim em relação à duração do áudio


def is_num(value: object) -> bool:
    if type(value) not in (int, float):  # bool fica de fora de propósito
        return False
    try:
        return math.isfinite(value)
    except OverflowError:  # inteiro gigante do JSON não é tempo válido
        return False


def check_audio(audio: object, errors: list[str]) -> float | None:
    """Valida o bloco audio e devolve a duração, ou None quando ela não serve."""
    if not isinstance(audio, dict):
        errors.append("audio deve ser um objeto")
        return None
    if not isinstance(audio.get("file"), str):
        errors.append("audio.file deve ser texto")
    if not is_num(audio.get("bpm")):
        errors.append("audio.bpm deve ser um número")
    duration = audio.get("duration")
    if not is_num(duration) or duration <= 0:
        errors.append("audio.duration deve ser um número maior que zero")
        return None
    return float(duration)


def check_line(line: object, index: int, duration: float | None, previous_start: float | None, errors: list[str]) -> float | None:
    """Valida uma linha e devolve o start dela, ou None quando não dá para usá-lo."""
    where = f"linha {index}"
    if not isinstance(line, dict):
        errors.append(f"{where}: deve ser um objeto")
        return None
    if type(line.get("id")) is not int or line["id"] != index:
        errors.append(f"{where}: id deve ser {index} (sequencial a partir de 0)")
    if not isinstance(line.get("text"), str):
        errors.append(f"{where}: text deve ser texto")
    if not isinstance(line.get("section"), str) or line["section"] not in SECTIONS:
        errors.append(f"{where}: section deve ser uma de: {', '.join(sorted(SECTIONS))}")
    words = check_words(line.get("words"), where, duration, errors)
    start, end = line.get("start"), line.get("end")
    if not is_num(start) or not is_num(end):
        errors.append(f"{where}: start e end devem ser números")
        return None
    if not 0 <= start < end or (duration is not None and end > duration + END_TOLERANCE):
        errors.append(f"{where}: precisa de 0 <= start < end <= duração do áudio")
    if previous_start is not None and start < previous_start:
        errors.append(f"{where}: start menor que o da linha anterior")
    if words and (start != words[0]["start"] or end != words[-1]["end"]):
        errors.append(f"{where}: start e end devem ser os da primeira e da última palavra")
    return start


def check_words(words: object, where: str, duration: float | None, errors: list[str]) -> list | None:
    """Valida as palavras de uma linha. Devolve a lista só se todas estiverem certas."""
    if not isinstance(words, list) or not words:
        errors.append(f"{where}: words deve ser uma lista não vazia")
        return None
    valid = True
    previous = None
    for number, word in enumerate(words):
        label = f"{where}, palavra {number}"
        if not isinstance(word, dict) or not isinstance(word.get("text"), str) or not is_num(word.get("start")) or not is_num(word.get("end")):
            errors.append(f"{label}: precisa de text, start e end")
            return None
        start, end = word["start"], word["end"]
        if not 0 <= start <= end or (duration is not None and end > duration + END_TOLERANCE):
            errors.append(f"{label}: precisa de 0 <= start <= end <= duração do áudio")
            valid = False
        if previous is not None and start < previous:
            errors.append(f"{label}: start menor que o da palavra anterior")
            valid = False
        previous = start
    return words if valid else None


def check_theme(theme: object, errors: list[str]) -> None:
    if not isinstance(theme, dict):
        errors.append("theme deve ser null ou um objeto")
        return
    for key in ("title", "mood", "visual_concept"):
        if not isinstance(theme.get(key), str):
            errors.append(f"theme.{key} deve ser texto")
    keywords = theme.get("keywords")
    if not isinstance(keywords, list) or not all(isinstance(word, str) for word in keywords):
        errors.append("theme.keywords deve ser uma lista de textos")
    palette = theme.get("palette")
    if not isinstance(palette, list) or not 3 <= len(palette) <= 5 or not all(isinstance(c, str) and HEX_COLOR.fullmatch(c) for c in palette):
        errors.append("theme.palette deve ter de 3 a 5 cores hexadecimais, como #1B1B3A")
    font = theme.get("font")
    if not isinstance(font, str) or font not in FONTS:
        errors.append(f"theme.font deve ser uma de: {', '.join(sorted(FONTS))}")
