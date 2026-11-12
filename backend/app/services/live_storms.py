"""Live moving storm cells over the Caspian (synthetic demo)."""

from __future__ import annotations

import json
import math
import random
import time
import uuid
from pathlib import Path

STORE = Path(__file__).resolve().parents[2] / "data" / "live_storms.json"

# Storm field advances at most once per interval (live demo pacing)
STORM_INTERVAL_SEC = 150  # 2.5 minutes

# Keep cells inside Caspian basin
LAT_MIN, LAT_MAX = 37.2, 46.0
LON_MIN, LON_MAX = 47.4, 53.4

SEED_CELLS = [
    {
        "id": "storm_north",
        "name": "Северный фронт",
        "lat": 44.6,
        "lon": 48.9,
        "vx": 0.035,  # deg lat per tick (~4s)
        "vy": 0.045,
        "wind_ms": 17.0,
        "severity": 0.82,
        "baseline": 0.82,
        "radius_km": 95.0,
        "kind": "storm",
        "phase": 0.2,
    },
    {
        "id": "storm_central",
        "name": "Центральный циклон",
        "lat": 41.8,
        "lon": 50.2,
        "vx": -0.02,
        "vy": 0.03,
        "wind_ms": 14.5,
        "severity": 0.72,
        "baseline": 0.72,
        "radius_km": 80.0,
        "kind": "storm",
        "phase": 1.1,
    },
    {
        "id": "storm_south",
        "name": "Южное волнение",
        "lat": 38.6,
        "lon": 49.7,
        "vx": 0.025,
        "vy": -0.02,
        "wind_ms": 12.5,
        "severity": 0.58,
        "baseline": 0.58,
        "radius_km": 70.0,
        "kind": "wave",
        "phase": 2.4,
    },
]


def _clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


def _load() -> dict:
    if not STORE.exists():
        return {"tick": 0, "updated_at": time.time(), "cells": [dict(c) for c in SEED_CELLS]}
    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
        if not data.get("cells"):
            data["cells"] = [dict(c) for c in SEED_CELLS]
        return data
    except Exception:
        return {"tick": 0, "updated_at": time.time(), "cells": [dict(c) for c in SEED_CELLS]}


def _save(data: dict) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_cells() -> list[dict]:
    return list(_load().get("cells") or [])


def advance_storms(*, dt: float = 1.0, force: bool = False) -> list[dict]:
    """Move / intensify storm cells at most every STORM_INTERVAL_SEC (~2–3 min)."""
    data = _load()
    cells: list[dict] = data.get("cells") or [dict(c) for c in SEED_CELLS]
    now = time.time()
    last = float(data.get("updated_at") or 0)
    if not force and cells and (now - last) < STORM_INTERVAL_SEC:
        return cells

    # One paced step ≈ noticeable drift over 2–3 minutes
    step = max(dt, 2.8)
    tick = int(data.get("tick") or 0) + 1
    rng = random.Random(tick * 9973)

    next_cells: list[dict] = []
    for c in cells:
        phase = float(c.get("phase") or 0) + 0.35 * step
        # Intensity breathes but stays meaningful for demo
        breath = 0.55 + 0.45 * math.sin(phase)
        base_sev = float(c.get("severity") or 0.55)
        # Keep a remembered baseline so cells don't permanently fade out
        baseline = float(c.get("baseline") or base_sev)
        severity = _clamp(baseline * 0.55 + breath * 0.5 + rng.uniform(-0.03, 0.05), 0.35, 0.97)
        wind = _clamp(9 + severity * 13 + rng.uniform(-0.6, 0.9), 8.0, 24.0)
        radius = _clamp(60 + severity * 50 + 10 * math.sin(phase * 0.7), 55.0, 130.0)

        vx = float(c.get("vx") or 0.02)
        vy = float(c.get("vy") or 0.02)
        # Slight steering drift
        vx += rng.uniform(-0.01, 0.01) * step
        vy += rng.uniform(-0.01, 0.01) * step
        vx = _clamp(vx, -0.08, 0.08)
        vy = _clamp(vy, -0.08, 0.08)

        lat = float(c["lat"]) + vx * step
        lon = float(c["lon"]) + vy * step

        # Bounce inside Caspian
        if lat < LAT_MIN or lat > LAT_MAX:
            vx *= -1
            lat = _clamp(lat, LAT_MIN, LAT_MAX)
        if lon < LON_MIN or lon > LON_MAX:
            vy *= -1
            lon = _clamp(lon, LON_MIN, LON_MAX)

        kind = "storm" if severity >= 0.72 else "wind" if wind >= 12 else "wave"

        next_cells.append(
            {
                **c,
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "vx": round(vx, 5),
                "vy": round(vy, 5),
                "wind_ms": round(wind, 1),
                "severity": round(severity, 3),
                "baseline": round(baseline, 3),
                "radius_km": round(radius, 1),
                "kind": kind,
                "phase": round(phase, 3),
            }
        )

    # Occasionally spawn a short-lived cell (paced steps, not every GPS tick)
    if tick % 4 == 0 and len(next_cells) < 5:
        next_cells.append(
            {
                "id": f"storm_{uuid.uuid4().hex[:6]}",
                "name": "Локальный шквал",
                "lat": round(rng.uniform(38.5, 44.5), 4),
                "lon": round(rng.uniform(48.2, 51.8), 4),
                "vx": round(rng.uniform(-0.04, 0.04), 5),
                "vy": round(rng.uniform(-0.04, 0.04), 5),
                "wind_ms": round(rng.uniform(12, 19), 1),
                "severity": round(rng.uniform(0.55, 0.85), 3),
                "radius_km": round(rng.uniform(55, 90), 1),
                "kind": "storm",
                "phase": round(rng.random() * 3, 3),
                "ttl": 3,  # ~3 paced steps ≈ 7–9 minutes
            }
        )

    kept: list[dict] = []
    for c in next_cells:
        ttl = c.get("ttl")
        if ttl is not None:
            ttl = int(ttl) - 1
            if ttl <= 0:
                continue
            c["ttl"] = ttl
        kept.append(c)

    # Ensure at least 2 cells always
    if len(kept) < 2:
        kept = [dict(c) for c in SEED_CELLS[:2]]

    data = {"tick": tick, "updated_at": time.time(), "cells": kept}
    _save(data)
    return kept


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def cells_affecting(lat: float, lon: float, cells: list[dict] | None = None) -> list[dict]:
    cells = cells if cells is not None else get_cells()
    hit = []
    for c in cells:
        if haversine_km(lat, lon, float(c["lat"]), float(c["lon"])) <= float(c.get("radius_km") or 70) * 1.15:
            hit.append(c)
    return hit
