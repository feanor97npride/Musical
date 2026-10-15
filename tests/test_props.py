# Testes do props.json: cópia do áudio, clip, nome sem acentos e validação do song.json.
import json
from pathlib import Path

import pytest

from engine.props import build_props


def valid_song() -> dict:
    return {
        "version": 1,
        "language": "pt",
        "audio": {"file": "musica.mp3", "duration": 10.0, "bpm": 96.0},
        "lines": [
            {"id": 0, "text": "Primeiro verso", "section": "verse", "start": 1.0, "end": 2.5,
             "words": [{"text": "Primeiro", "start": 1.0, "end": 1.5}, {"text": "verso", "start": 1.5, "end": 2.5}]},
        ],
        "theme": None,
    }


@pytest.fixture
def files(tmp_path: Path) -> tuple[Path, Path, Path]:
    song = tmp_path / "song.json"
    song.write_text(json.dumps(valid_song()), encoding="utf-8")
    audio = tmp_path / "Tua Presença.mp3"
    audio.write_bytes(b"ID3fake")
    return song, audio, tmp_path / "public"


def test_com_clip_copia_audio_e_monta_contrato(files):
    song, audio, public = files
    props = build_props(song, audio, "highlight", "solid", (1.0, 5.0), public_audio=public)
    assert props["audioFile"].startswith("audio/tua-presenca-") and props["audioFile"].endswith(".mp3")
    assert (public / props["audioFile"].removeprefix("audio/")).read_bytes() == b"ID3fake"
    assert props["clip"] == {"start": 1.0, "end": 5.0}
    assert props["style"] == {"subtitle": "highlight", "background": "solid"}
    assert props["song"]["version"] == 1


def test_sem_clip_fica_null(files):
    song, audio, public = files
    assert build_props(song, audio, public_audio=public)["clip"] is None


def test_song_invalido_e_recusado(files):
    song, audio, public = files
    bad = valid_song()
    bad["version"] = 2
    song.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="song.json inválido"):
        build_props(song, audio, public_audio=public)


def test_estilo_fundo_e_clip_invalidos_sao_recusados(files):
    song, audio, public = files
    with pytest.raises(ValueError, match="estilo"):
        build_props(song, audio, "xpto", public_audio=public)
    with pytest.raises(ValueError, match="fundo"):
        build_props(song, audio, background="radial", public_audio=public)
    with pytest.raises(ValueError, match="clip"):
        build_props(song, audio, clip=(5.0, 1.0), public_audio=public)
    with pytest.raises(ValueError, match="clip"):
        build_props(song, audio, clip=(0.0, 999.0), public_audio=public)
