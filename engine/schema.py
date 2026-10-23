# Dataclasses e validate_song(): contrato do song.json.
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from engine.checks import check_audio, check_line, check_theme, is_num


@dataclass
class Word:
    text: str
    start: float
    end: float

    def to_dict(self) -> dict:
        return {"text": self.text, "start": self.start, "end": self.end}

    @classmethod
    def from_dict(cls, data: dict) -> Word:
        return cls(data["text"], float(data["start"]), float(data["end"]))


@dataclass
class Line:
    id: int
    text: str
    section: str
    start: float
    end: float
    words: list[Word]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "section": self.section,
            "start": self.start,
            "end": self.end,
            "words": [word.to_dict() for word in self.words],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Line:
        words = [Word.from_dict(word) for word in data["words"]]
        return cls(data["id"], data["text"], data["section"], float(data["start"]), float(data["end"]), words)


@dataclass
class Audio:
    file: str
    duration: float
    bpm: float

    def to_dict(self) -> dict:
        return {"file": self.file, "duration": self.duration, "bpm": self.bpm}

    @classmethod
    def from_dict(cls, data: dict) -> Audio:
        return cls(data["file"], float(data["duration"]), float(data["bpm"]))


@dataclass
class Theme:
    title: str
    mood: str
    keywords: list[str]
    palette: list[str]
    font: str
    visual_concept: str

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "mood": self.mood,
            "keywords": self.keywords,
            "palette": self.palette,
            "font": self.font,
            "visual_concept": self.visual_concept,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Theme:
        return cls(data["title"], data["mood"], list(data["keywords"]), list(data["palette"]), data["font"], data["visual_concept"])


@dataclass
class Song:
    language: str
    audio: Audio
    lines: list[Line]
    theme: Theme | None = None
    version: int = 1

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "language": self.language,
            "audio": self.audio.to_dict(),
            "lines": [line.to_dict() for line in self.lines],
            "theme": self.theme.to_dict() if self.theme is not None else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Song:
        theme = Theme.from_dict(data["theme"]) if data.get("theme") is not None else None
        lines = [Line.from_dict(line) for line in data["lines"]]
        return cls(data["language"], Audio.from_dict(data["audio"]), lines, theme, data["version"])


def write_song(path: Path, song: dict) -> None:
    errors = validate_song(song)
    if errors:
        raise ValueError("song.json inválido: " + "; ".join(errors))
    tmp = path.with_suffix(".tmp.json")  # troca só no fim: um corte no meio não deixa JSON truncado no cache
    tmp.write_text(json.dumps(song, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def valid_song_file(path: Path) -> bool:
    """Um song.json truncado ou inválido não serve de cache."""
    try:
        return not validate_song(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return False


def validate_song(data: dict) -> list[str]:
    """Devolve os erros do song.json; lista vazia quando válido. Nunca lança exceção."""
    if not isinstance(data, dict):
        return ["song.json deve ser um objeto"]
    errors: list[str] = []
    if not is_num(data.get("version")) or data["version"] != 1:
        errors.append("version deve ser 1")
    if not isinstance(data.get("language"), str):
        errors.append("language deve ser texto")
    duration = check_audio(data.get("audio"), errors)
    lines = data.get("lines")
    if not isinstance(lines, list) or not lines:
        errors.append("lines deve ser uma lista não vazia")
        lines = []
    previous_start = None
    for index, line in enumerate(lines):
        start = check_line(line, index, duration, previous_start, errors)
        previous_start = start if start is not None else previous_start
    if data.get("theme") is not None:
        check_theme(data["theme"], errors)
    return errors
