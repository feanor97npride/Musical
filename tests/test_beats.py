# Testes das batidas: um clique sintético a cada meio segundo, e a validação do campo audio.beats.
import numpy as np
import pytest
import soundfile as sf

from engine.audio import beats
from engine.schema import validate_song


def clicks(path, seconds=10.0, interval=0.5, sr=22050):
    # sem ruído de fundo, o librosa não estima o tempo; com ruído, o sinal fica parecido com música
    rng = np.random.default_rng(0)
    y = (rng.standard_normal(int(seconds * sr)) * 0.05).astype(np.float32)
    t = np.arange(int(0.08 * sr)) / sr
    burst = (np.sin(2 * np.pi * 110 * t) * np.exp(-t * 40)).astype(np.float32)  # um pulso grave em cada batida
    for start in np.arange(0.0, seconds, interval):
        index = int(start * sr)
        y[index:index + len(burst)] += burst
    sf.write(path, y, sr)


def song_com_batidas(batidas):
    return {
        "version": 1,
        "language": "pt",
        "audio": {"file": "musica.mp3", "duration": 10.0, "bpm": 120.0, "beats": batidas},
        "lines": [{"id": 0, "text": "oi", "section": "verse", "start": 1.0, "end": 2.0,
                   "words": [{"text": "oi", "start": 1.0, "end": 2.0}]}],
        "theme": None,
    }


def test_batidas_de_um_clique_a_cada_meio_segundo(tmp_path):
    wav = tmp_path / "cliques.wav"
    clicks(wav)
    found = beats(wav)
    assert len(found) >= 15
    assert np.median(np.diff(found)) == pytest.approx(0.5, abs=0.05)


def test_batidas_em_ordem_e_dentro_da_musica_passam():
    assert validate_song(song_com_batidas([0.5, 1.0, 1.5])) == []


def test_batidas_fora_de_ordem_sao_recusadas():
    assert validate_song(song_com_batidas([1.0, 0.5]))


def test_batida_depois_do_fim_da_musica_e_recusada():
    assert validate_song(song_com_batidas([11.0]))
