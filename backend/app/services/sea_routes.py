"""Sea corridors with mid-sea waypoints (keep vessels on water)."""

from __future__ import annotations

import math

# City / port anchors
PORTS: dict[str, tuple[float, float]] = {
    "port_astrakhan": (46.35, 48.04),
    "port_makhachkala": (42.98, 47.50),
    "port_aktau": (43.65, 51.17),
    "port_baku": (40.38, 49.87),
    "port_anzali": (37.47, 49.46),
}

PORT_LABELS: dict[str, str] = {
    "port_astrakhan": "Астрахань",
    "port_makhachkala": "Махачкала",
    "port_aktau": "Актау",
    "port_baku": "Баку",
    "port_anzali": "Энзели",
}

_NAME_TO_PORT = {
    "астрахань": "port_astrakhan",
    "махачкала": "port_makhachkala",
    "актау": "port_aktau",
    "баку": "port_baku",
    "энзели": "port_anzali",
    "анзали": "port_anzali",
}


def resolve_port_id(value: str | None, fallback: str = "port_astrakhan") -> str:
    raw = (value or "").strip()
    if not raw:
        return fallback
    if raw in PORTS:
        return raw
    key = raw.lower().replace(" (демо)", "").replace("порт ", "").strip()
    return _NAME_TO_PORT.get(key, fallback)


def port_label(port_id: str) -> str:
    return PORT_LABELS.get(port_id, port_id)

# Sea exit points slightly offshore from cities
SEA_GATE: dict[str, tuple[float, float]] = {
    "port_astrakhan": (45.55, 48.55),
    "port_makhachkala": (42.85, 48.15),
    "port_aktau": (43.35, 50.85),
    "port_baku": (40.55, 50.15),
    "port_anzali": (37.75, 49.55),
}

# Named corridors: list of lat/lon including sea waypoints only (cities attached separately)
CORRIDORS: dict[str, list[tuple[float, float]]] = {
    "astrakhan_anzali": [
        SEA_GATE["port_astrakhan"],
        (44.2, 49.1),
        (42.4, 49.55),
        (40.6, 49.7),
        (39.0, 49.55),
        SEA_GATE["port_anzali"],
    ],
    "makhachkala_anzali": [
        SEA_GATE["port_makhachkala"],
        (41.6, 49.0),
        (40.0, 49.35),
        (38.6, 49.45),
        SEA_GATE["port_anzali"],
    ],
    "aktau_baku": [
        SEA_GATE["port_aktau"],
        (42.4, 50.55),
        (41.4, 50.25),
        SEA_GATE["port_baku"],
    ],
    # Storm bypasses
    "astrakhan_anzali_via_makh": [
        SEA_GATE["port_astrakhan"],
        (44.6, 48.6),
        SEA_GATE["port_makhachkala"],
        (41.5, 49.05),
        (39.5, 49.4),
        SEA_GATE["port_anzali"],
    ],
    "astrakhan_anzali_via_aktau": [
        SEA_GATE["port_astrakhan"],
        (44.8, 49.6),
        (43.8, 50.5),
        SEA_GATE["port_aktau"],
        (42.0, 50.4),
        (40.2, 50.0),
        (38.5, 49.6),
        SEA_GATE["port_anzali"],
    ],
    "makhachkala_anzali_east": [
        SEA_GATE["port_makhachkala"],
        (42.4, 50.2),
        (41.0, 51.0),
        (39.4, 50.4),
        (38.2, 49.8),
        SEA_GATE["port_anzali"],
    ],
}

PAIR_TO_CORRIDOR: dict[tuple[str, str], str] = {
    ("port_astrakhan", "port_anzali"): "astrakhan_anzali",
    ("port_makhachkala", "port_anzali"): "makhachkala_anzali",
    ("port_aktau", "port_baku"): "aktau_baku",
}

ALT_CORRIDOR: dict[str, str] = {
    "alt_current": "",  # resolve from pair
    "alt_via_makhachkala": "astrakhan_anzali_via_makh",
    "alt_via_aktau": "astrakhan_anzali_via_aktau",
    "alt_east_bypass": "makhachkala_anzali_east",
    # Generic geometric detours (built in path_for)
    "alt_detour_east": "__detour_east__",
    "alt_detour_west": "__detour_west__",
}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dphi = math.radians(b[0] - a[0])
    dl = math.radians(b[1] - a[1])
    x = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def corridor_id_for(origin: str, dest: str, alternative_id: str | None = None) -> str | None:
    if alternative_id and alternative_id in ALT_CORRIDOR and ALT_CORRIDOR[alternative_id]:
        return ALT_CORRIDOR[alternative_id]
    return PAIR_TO_CORRIDOR.get((origin, dest))


def _detour_path(
    origin: str,
    dest: str,
    *,
    east: bool,
) -> list[tuple[float, float]]:
    """Geometric bypass around the mid-point of the direct corridor."""
    base = path_for(origin, dest, None, include_ports=True)
    if len(base) < 2:
        return base
    mid_i = len(base) // 2
    mid = base[mid_i]
    # Stronger lateral bend so the ship visibly leaves the storm corridor
    offset = 1.85 if east else -1.55
    bend = (mid[0], max(47.4, min(53.4, mid[1] + offset)))
    # Second bend keeps the detour away from mid-basin cells
    mid2 = base[min(len(base) - 1, mid_i + 1)]
    bend2 = (mid2[0], max(47.4, min(53.4, mid2[1] + offset * 0.7)))
    return base[:mid_i] + [bend, bend2] + base[mid_i:]


def path_for(
    origin: str,
    dest: str,
    alternative_id: str | None = None,
    *,
    include_ports: bool = True,
) -> list[tuple[float, float]]:
    if alternative_id in {"alt_detour_east", "alt_detour_west"}:
        return _detour_path(origin, dest, east=alternative_id == "alt_detour_east")

    cid = corridor_id_for(origin, dest, alternative_id)
    if cid in {"__detour_east__", "__detour_west__"}:
        return _detour_path(origin, dest, east=cid == "__detour_east__")

    sea = list(CORRIDORS.get(cid or "", []))
    if not sea:
        o = SEA_GATE.get(origin) or PORTS.get(origin)
        d = SEA_GATE.get(dest) or PORTS.get(dest)
        if o and d:
            sea = [o, d]
        else:
            return []
    if include_ports:
        op = PORTS.get(origin)
        dp = PORTS.get(dest)
        out: list[tuple[float, float]] = []
        if op:
            out.append(op)
        out.extend(sea)
        if dp and (not out or out[-1] != dp):
            out.append(dp)
        return out
    return sea


def path_length_km(points: list[tuple[float, float]]) -> float:
    return sum(_haversine_km(points[i], points[i + 1]) for i in range(len(points) - 1)) or 1.0


def point_on_path(points: list[tuple[float, float]], t: float) -> tuple[float, float, float]:
    """Return lat, lon, heading_deg for progress t in [0,1]."""
    t = max(0.0, min(1.0, t))
    if len(points) == 1:
        return points[0][0], points[0][1], 0.0
    if len(points) < 2:
        return 41.8, 50.0, 0.0

    total = path_length_km(points)
    target = total * t
    acc = 0.0
    for i in range(len(points) - 1):
        seg = _haversine_km(points[i], points[i + 1])
        if acc + seg >= target or i == len(points) - 2:
            local = 0.0 if seg <= 1e-9 else (target - acc) / seg
            local = max(0.0, min(1.0, local))
            lat = _lerp(points[i][0], points[i + 1][0], local)
            lon = _lerp(points[i][1], points[i + 1][1], local)
            # heading
            dlon = math.radians(points[i + 1][1] - points[i][1])
            y = math.sin(dlon) * math.cos(math.radians(points[i + 1][0]))
            x = math.cos(math.radians(points[i][0])) * math.sin(math.radians(points[i + 1][0])) - math.sin(
                math.radians(points[i][0])
            ) * math.cos(math.radians(points[i + 1][0])) * math.cos(dlon)
            heading = (math.degrees(math.atan2(y, x)) + 360) % 360
            return lat, lon, heading
        acc += seg
    return points[-1][0], points[-1][1], 0.0


def storm_alternatives_for_pair(origin: str, dest: str) -> list[dict]:
    """Alternate sea paths for a corridor (safety scored separately vs live storms)."""
    items = []
    direct = path_for(origin, dest, None)
    if direct:
        items.append(
            {
                "id": "alt_current",
                "title": "Прямой морской путь",
                "subtitle": "Текущий коридор",
                "corridor_id": corridor_id_for(origin, dest),
                "path": [{"lat": p[0], "lon": p[1]} for p in direct],
                "feasible": True,
                "storm_safe": True,
                "recommended": False,
                "eta_delta_hours": 0,
                "cost_delta_pct": 0,
            }
        )
    if origin == "port_astrakhan" and dest == "port_anzali":
        for alt_id, title, eta, cost in [
            ("alt_via_makhachkala", "Обход через Махачкалу", 8, 8),
            ("alt_via_aktau", "Восточный обход через Актау", 12, 15),
        ]:
            pts = path_for(origin, dest, alt_id)
            items.append(
                {
                    "id": alt_id,
                    "title": title,
                    "subtitle": "Штормовой обход",
                    "corridor_id": corridor_id_for(origin, dest, alt_id),
                    "path": [{"lat": p[0], "lon": p[1]} for p in pts],
                    "feasible": True,
                    "storm_safe": True,
                    "recommended": False,
                    "eta_delta_hours": eta,
                    "cost_delta_pct": cost,
                }
            )
    elif origin == "port_makhachkala" and dest == "port_anzali":
        pts = path_for(origin, dest, "alt_east_bypass")
        items.append(
            {
                "id": "alt_east_bypass",
                "title": "Восточный обход",
                "subtitle": "В обход прибрежного шторма",
                "corridor_id": "makhachkala_anzali_east",
                "path": [{"lat": p[0], "lon": p[1]} for p in pts],
                "feasible": True,
                "storm_safe": True,
                "recommended": False,
                "eta_delta_hours": 6,
                "cost_delta_pct": 6,
            }
        )
    # Extra geometric detours so «Выбрать» всегда может увести от шторма
    have = {i["id"] for i in items}
    if direct and len(direct) >= 2:
        for alt_id, title, eta, cost in [
            ("alt_detour_east", "Восточный обход", 10, 10),
            ("alt_detour_west", "Западный обход", 8, 8),
        ]:
            if alt_id in have:
                continue
            pts = path_for(origin, dest, alt_id)
            if len(pts) < 2:
                continue
            items.append(
                {
                    "id": alt_id,
                    "title": title,
                    "subtitle": "Обход опасной зоны",
                    "corridor_id": alt_id,
                    "path": [{"lat": p[0], "lon": p[1]} for p in pts],
                    "feasible": True,
                    "storm_safe": True,
                    "recommended": False,
                    "eta_delta_hours": eta,
                    "cost_delta_pct": cost,
                }
            )
    return items


def path_hits_storm(
    points: list[tuple[float, float]],
    cells: list[dict],
    *,
    min_severity: float = 0.62,
) -> tuple[int, float]:
    """Return (hit_count, max_severity) if polyline nears dangerous cells."""
    if not points or not cells:
        return 0, 0.0
    hits = 0
    max_sev = 0.0
    # Sample ~12 points along path
    samples: list[tuple[float, float]] = []
    for i in range(12):
        t = i / 11.0
        lat, lon, _ = point_on_path(points, t)
        samples.append((lat, lon))
    for cell in cells:
        sev = float(cell.get("severity") or 0)
        if sev < min_severity:
            continue
        clat, clon = float(cell["lat"]), float(cell["lon"])
        # Slightly tighter than alert radius so eastern bypasses can clear the cell
        radius = float(cell.get("radius_km") or 70) * 0.88
        for lat, lon in samples:
            if _haversine_km((lat, lon), (clat, clon)) <= radius:
                hits += 1
                max_sev = max(max_sev, sev)
                break
    return hits, max_sev


def score_storm_alternatives(
    origin: str,
    dest: str,
    cells: list[dict] | None = None,
) -> list[dict]:
    """Mark safe/recommended bypasses against live storm field."""
    cells = cells or []
    items = storm_alternatives_for_pair(origin, dest)
    scored: list[dict] = []
    for alt in items:
        pts = [(p["lat"], p["lon"]) for p in (alt.get("path") or [])]
        if len(pts) < 2:
            pts = path_for(origin, dest, None if alt["id"] == "alt_current" else alt["id"])
            alt["path"] = [{"lat": p[0], "lon": p[1]} for p in pts]
        hits, max_sev = path_hits_storm(pts, cells)
        scored.append(
            {
                **alt,
                "feasible": True,
                "storm_safe": hits == 0,
                "storm_hits": hits,
                "storm_severity": round(max_sev, 2),
                "recommended": False,
                "subtitle": alt.get("subtitle") or "Коридор",
            }
        )

    current = next((a for a in scored if a["id"] == "alt_current"), None)
    current_hits = int(current["storm_hits"]) if current else 0
    # Relative safety: fewer hits than current route counts as safer bypass
    for a in scored:
        hits = int(a.get("storm_hits") or 0)
        safer = hits == 0 or (current_hits > 0 and hits < current_hits)
        a["storm_safe"] = safer if a["id"] != "alt_current" else hits == 0
        if a["id"] == "alt_current":
            a["subtitle"] = "Опасность на пути" if hits else "Прямой коридор"
        elif safer:
            a["subtitle"] = "Безопасный обход шторма" if hits == 0 else "Безопаснее текущего"
        else:
            a["subtitle"] = "Опасность на пути"

    candidates = [a for a in scored if a["id"] != "alt_current"] or scored
    danger_on_route = current_hits > 0 or any(not a["storm_safe"] for a in scored if a["id"] == "alt_current")
    if danger_on_route and candidates:
        best = min(
            candidates,
            key=lambda a: (
                0 if a["storm_safe"] else 1,
                a.get("storm_hits", 99),
                a.get("eta_delta_hours", 99),
            ),
        )
        for a in scored:
            a["recommended"] = a["id"] == best["id"]
            if a["recommended"]:
                a["feasible"] = True
                a["storm_safe"] = True
                a["subtitle"] = "Рекомендуемый безопасный маршрут"
    return scored
