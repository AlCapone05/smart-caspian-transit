"""Persist Telegram chats that want live pushes from the website/API."""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "tg_subscribers.json"


def _load() -> dict:
    if not DATA.exists():
        return {"chats": [], "seen_ids": []}
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except Exception:
        return {"chats": [], "seen_ids": []}


def _save(data: dict) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_chats() -> list[int]:
    return [int(x) for x in _load().get("chats") or []]


def subscribe(chat_id: int) -> bool:
    data = _load()
    chats = set(int(x) for x in data.get("chats") or [])
    if chat_id in chats:
        return False
    chats.add(chat_id)
    data["chats"] = sorted(chats)
    _save(data)
    return True


def unsubscribe(chat_id: int) -> bool:
    data = _load()
    chats = set(int(x) for x in data.get("chats") or [])
    if chat_id not in chats:
        return False
    chats.discard(chat_id)
    data["chats"] = sorted(chats)
    _save(data)
    return True


def get_seen() -> set[str]:
    return set(str(x) for x in _load().get("seen_ids") or [])


def add_seen(ids: list[str], keep: int = 400) -> None:
    data = _load()
    seen = list(dict.fromkeys([*(data.get("seen_ids") or []), *ids]))
    data["seen_ids"] = seen[-keep:]
    _save(data)
