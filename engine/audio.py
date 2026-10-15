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
