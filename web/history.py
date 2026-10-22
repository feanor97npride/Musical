# Histórico das letras geradas com IA: guardado em output/historico/letras.json, no computador que roda o servidor.
import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from engine.pipeline import ROOT

HISTORY_FILE = ROOT / "output" / "historico" / "letras.json"
_lock = threading.Lock()  # as rotas rodam em threads diferentes; a escrita tem que ser uma de cada vez


def _read() -> list[dict]:
    try:
        items = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except ValueError:  # arquivo corrompido: guarda de lado em vez de apagar, e começa um novo
        HISTORY_FILE.replace(HISTORY_FILE.with_name("letras.corrompido.json"))
        return []
    return items if isinstance(items, list) else []


def _write(items: list[dict]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = HISTORY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, HISTORY_FILE)


def add(context: str, draft: dict) -> dict:
    item = {"id": uuid.uuid4().hex, "created_at": datetime.now().isoformat(timespec="seconds"),
            "context": context, **draft}
    with _lock:
        _write([item, *_read()])
    return item


def list_items() -> list[dict]:
    with _lock:
        items = _read()
    return [{"id": item["id"], "created_at": item["created_at"], "title": item.get("title", "")} for item in items]


def get(item_id: str) -> dict | None:
    with _lock:
        return next((item for item in _read() if item.get("id") == item_id), None)


def remove(item_id: str) -> bool:
    with _lock:
        items = _read()
        kept = [item for item in items if item.get("id") != item_id]
        if len(kept) == len(items):
            return False
        _write(kept)
    return True
