# Testes do motor (Pacote C): erros recusados cedo, cache de voz por áudio, marcadores e BPM de reserva.
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from engine import audio, lyrics, pipeline, separate, transcribe
from engine.schema import write_song


def wav(path: Path, seconds: float = 2.0, sr: int = 22050) -> Path:
    sf.write(path, np.zeros(int(seconds * sr), dtype=np.float32), sr)
    return path


def boom(*_args, **_kwargs):
    raise AssertionError("não devia rodar")


def test_estilo_desconhecido_e_recusado_antes_de_qualquer_etapa():
    with pytest.raises(SystemExit):  # argparse recusa com "invalid choice"
        pipeline.main(["--audio", "a.mp3", "--lyrics", "a.txt", "--style", "neon"])


def test_clip_invertido_e_recusado_antes_de_qualquer_etapa():
    with pytest.raises(SystemExit):
        pipeline.main(["--audio", "a.mp3", "--lyrics", "a.txt", "--clip", "30:10"])


def test_clip_depois_do_fim_da_musica_para_antes_da_separacao(tmp_path, monkeypatch):
    audio_file = wav(tmp_path / "musica.wav", seconds=2.0)
    lyrics_file = tmp_path / "letra.txt"
    lyrics_file.write_text("um\ndois", encoding="utf-8")
    monkeypatch.setattr(pipeline, "_separate", boom)
    assert pipeline.main(["--audio", str(audio_file), "--lyrics", str(lyrics_file), "--clip", "0:10"]) == 1


def test_letra_sem_versos_para_antes_da_separacao(tmp_path, monkeypatch):
    lyrics_file = tmp_path / "letra.txt"
    lyrics_file.write_text("[Refrão]\n\n", encoding="utf-8")
    monkeypatch.setattr(pipeline, "_separate", boom)
    assert pipeline.main(["--audio", "a.mp3", "--lyrics", str(lyrics_file)]) == 1


def test_letra_que_nao_e_utf8_da_erro_claro(tmp_path, monkeypatch):
    lyrics_file = tmp_path / "letra.txt"
    lyrics_file.write_bytes(b"\xff\xfe\x00 lixo")
    monkeypatch.setattr(pipeline, "_separate", boom)
    assert pipeline.main(["--audio", "a.mp3", "--lyrics", str(lyrics_file)]) == 1


def test_marcadores_em_portugues_viram_secao():
    text = "[Coro]\na\n[Estrofe 1]\nb\n[Pré-refrão]\nc\n[Refrao]\nd"
    assert [line["section"] for line in lyrics.parse_lyrics(text)] == ["chorus", "verse", "verse", "chorus"]


def test_marcador_desconhecido_e_apontado():
    assert lyrics.unknown_markers("[Solo]\n[Coro]\n[Ponte]\nverso") == ["Solo"]


def test_voz_fica_no_cache_do_audio_e_some_a_pasta_do_demucs(tmp_path, monkeypatch):
    audio_file = tmp_path / "musica.mp3"
    audio_file.write_bytes(b"audio")
    monkeypatch.setattr(separate, "VOICE_CACHE", tmp_path / "voz")

    def demucs_falso(cmd, check):  # grava a voz onde o Demucs gravaria de verdade
        saida = Path(cmd[cmd.index("-o") + 1]) / "htdemucs" / "musica" / "vocals.wav"
        saida.parent.mkdir(parents=True)
        saida.write_bytes(b"voz")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(separate.subprocess, "run", demucs_falso)
    destino = tmp_path / "voz" / "pasta"
    assert separate.separate_vocals(audio_file, destino).read_bytes() == b"voz"
    assert not (destino / "demucs").exists()
    assert not (destino / "vocals.tmp.wav").exists()


def test_demucs_sem_saida_da_erro_claro(tmp_path, monkeypatch):
    audio_file = tmp_path / "musica.mp3"
    audio_file.write_bytes(b"audio")
    monkeypatch.setattr(separate.subprocess, "run", lambda cmd, check: subprocess.CompletedProcess(cmd, 0))
    with pytest.raises(RuntimeError, match="vocals.wav"):
        separate.separate_vocals(audio_file, tmp_path / "pasta")


def test_cache_da_voz_depende_do_conteudo_do_audio(tmp_path, monkeypatch):
    monkeypatch.setattr(separate, "VOICE_CACHE", tmp_path / "voz")
    primeiro = tmp_path / "a.mp3"
    primeiro.write_bytes(b"mesmo")
    copia = tmp_path / "b.mp3"
    copia.write_bytes(b"mesmo")
    outro = tmp_path / "c.mp3"
    outro.write_bytes(b"outro")
    assert separate.voice_dir(primeiro) == separate.voice_dir(copia)
    assert separate.voice_dir(primeiro) != separate.voice_dir(outro)


def test_transcricao_sem_fala_nao_grava_arquivo(tmp_path, monkeypatch):
    audio_file = tmp_path / "musica.mp3"
    audio_file.write_bytes(b"audio")
    out = tmp_path / "letra.txt"
    monkeypatch.setattr(transcribe, "separate_vocals", lambda audio_path, out_dir, force=False: tmp_path / "v.wav")
    monkeypatch.setattr(transcribe, "words", lambda *args, **kwargs: [])
    assert transcribe.main(["--audio", str(audio_file), "--out", str(out)]) == 1
    assert not out.exists()


def test_force_refaz_a_voz_na_transcricao(tmp_path, monkeypatch):
    audio_file = tmp_path / "musica.mp3"
    audio_file.write_bytes(b"audio")
    recebidos = []

    def separar(audio_path, out_dir, force=False):
        recebidos.append(force)
        return tmp_path / "v.wav"

    monkeypatch.setattr(transcribe, "separate_vocals", separar)
    monkeypatch.setattr(transcribe, "words", lambda *args, **kwargs: [("oi", 0.0, 1.0)])
    assert transcribe.main(["--audio", str(audio_file), "--out", str(tmp_path / "l.txt"), "--force"]) == 0
    assert recebidos == [True]


def test_bpm_de_reserva_para_musica_sem_batida(tmp_path, monkeypatch):
    silencio = wav(tmp_path / "silencio.wav")
    monkeypatch.setattr(audio.librosa.beat, "beat_track", lambda **kwargs: (0.0, np.array([])))
    assert audio.bpm(silencio) == audio.FALLBACK_BPM
    assert audio.beats(silencio) == []


def test_write_song_nao_deixa_arquivo_temporario(tmp_path):
    song = {"version": 1, "language": "pt", "audio": {"file": "musica.mp3", "duration": 10.0, "bpm": 96.0},
            "lines": [{"id": 0, "text": "um", "section": "verse", "start": 1.0, "end": 2.0,
                       "words": [{"text": "um", "start": 1.0, "end": 2.0}]}],
            "theme": None}
    write_song(tmp_path / "song.json", song)
    assert json.loads((tmp_path / "song.json").read_text(encoding="utf-8")) == song
    assert not (tmp_path / "song.tmp.json").exists()
