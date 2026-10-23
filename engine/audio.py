# Duração e BPM do áudio com librosa.
from pathlib import Path

import librosa
import numpy as np


def duration(audio: Path) -> float:
    return float(librosa.get_duration(path=str(audio)))


FALLBACK_BPM = 120.0  # shortcut: música sem batida detectada (silêncio, só voz) usa 120; subir se o ritmo do vídeo ficar estranho


def bpm(audio: Path) -> float:
    y, sr = librosa.load(str(audio))
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    value = float(np.atleast_1d(tempo)[0])  # versões novas do librosa devolvem array
    return value if value > 0 else FALLBACK_BPM  # 0 = sem batida: o song.json exige um bpm positivo


def beats(audio: Path) -> list[float]:
    """Tempos das batidas, em segundos. shortcut: pode errar o tempo (dobro ou metade) em ritmo irregular."""
    y, sr = librosa.load(str(audio))
    _, times = librosa.beat.beat_track(y=y, sr=sr, units="time")
    return [round(float(time), 3) for time in times]
