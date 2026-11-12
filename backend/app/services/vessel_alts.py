"""Persist vessel-level storm route choices (demo JSON)."""

from __future__ import annotations

import json
from pathlib import Path

STORE = Path(__file__).resolve().parents[2] / "data" / "vessel_route_alts.json"


def load_alts() -> dict[str, str]:
    if not STORE.exists():
        return {}
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_alt(vessel_id: str) -> str | None:
    return load_alts().get(vessel_id)


def set_alt(vessel_id: str, alternative_id: str | None) -> dict[str, str]:
    data = load_alts()
    if not alternative_id or alternative_id == "alt_current":
        data.pop(vessel_id, None)
    else:
        data[vessel_id] = alternative_id
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
