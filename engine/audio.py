# Duração e BPM do áudio com librosa.
from pathlib import Path

import librosa
import numpy as np


def duration(audio: Path) -> float:
    return float(librosa.get_duration(path=str(audio)))


def bpm(audio: Path) -> float:
    y, sr = librosa.load(str(audio))
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(np.atleast_1d(tempo)[0])  # versões novas do librosa devolvem array


def beats(audio: Path) -> list[float]:
    """Tempos das batidas, em segundos. shortcut: pode errar o tempo (dobro ou metade) em ritmo irregular."""
    y, sr = librosa.load(str(audio))
    _, times = librosa.beat.beat_track(y=y, sr=sr, units="time")
    return [round(float(time), 3) for time in times]
