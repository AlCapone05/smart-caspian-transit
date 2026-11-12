"""Synthetic GPS vessel tracker + predictive weather alerts (Caspian demo)."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Port, Shipment, Vessel, WeatherAlert, WeatherForecast
from app.services.sea_routes import (
    PORTS as PORT_COORDS,
    path_for,
    path_length_km,
    point_on_path,
    score_storm_alternatives,
    storm_alternatives_for_pair,
)
from app.services.vessel_alts import get_alt, set_alt
from app.services.live_storms import advance_storms, cells_affecting, get_cells, haversine_km

MSK = ZoneInfo("Europe/Moscow")

# Hand-aligned SVG points matching LiveCaspianMap (viewBox 0 0 696 320)
PORT_MAP_XY = {
    "port_astrakhan": (270.0, 62.0),
    "port_makhachkala": (252.0, 155.0),
    "port_aktau": (430.0, 118.0),
    "port_baku": (248.0, 220.0),
    "port_anzali": (348.0, 262.0),
}


def project_to_map(lat: float, lon: float, port_id: str | None = None) -> dict:
    """Prefer schematic port anchor; otherwise soft geo fallback."""
    if port_id and port_id in PORT_MAP_XY:
        x, y = PORT_MAP_XY[port_id]
        return {"x": x, "y": y}
    # soft fallback kept near sea basin
    x = 200 + (lon - 47.0) / 5.0 * 220
    y = 40 + (47.0 - lat) / 10.0 * 200
    return {"x": round(max(40, min(650, x)), 1), "y": round(max(30, min(250, y)), 1)}


def vessel_map_xy(v: Vessel) -> dict:
    """Interpolate on schematic corridor so markers sit on the drawn sea."""
    o = PORT_MAP_XY.get(v.origin_port_id)
    d = PORT_MAP_XY.get(v.destination_port_id)
    t = max(0.0, min(1.0, float(v.progress or 0)))
    if o and d:
        if v.origin_port_id == v.destination_port_id:
            x, y = o
        else:
            x = _lerp(o[0], d[0], t)
            y = _lerp(o[1], d[1], t)
            # light perpendicular wobble along route (keeps track “alive” but on-map)
            dx, dy = d[0] - o[0], d[1] - o[1]
            length = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / length, dx / length
            wobble = math.sin(t * math.pi * 2) * 6.0
            x += nx * wobble
            y += ny * wobble
        return {"x": round(x, 1), "y": round(y, 1)}
    return project_to_map(v.lat, v.lon)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _heading(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _msk_label(dt: datetime) -> str:
    local = _aware(dt).astimezone(MSK)
    return local.strftime("%d.%m %H:%M")


async def ensure_tracking_data(session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    existing = (await session.execute(select(Vessel).limit(1))).scalar_one_or_none()
    if not existing:
        vessels = [
            Vessel(
                id="ves_caspian_star",
                name="Caspian Star",
                mmsi="273312100",
                shipment_id="shp_sct_2048",
                route_label="Астрахань → Энзели",
                origin_port_id="port_astrakhan",
                destination_port_id="port_anzali",
                status="underway",
                lat=point_on_path(path_for("port_astrakhan", "port_anzali"), 0.28)[0],
                lon=point_on_path(path_for("port_astrakhan", "port_anzali"), 0.28)[1],
                heading_deg=point_on_path(path_for("port_astrakhan", "port_anzali"), 0.28)[2],
                speed_knots=11.5,
                progress=0.28,
                updated_at=now,
            ),
            Vessel(
                id="ves_aktau_ferry",
                name="Aktau Express",
                mmsi="436000450",
                shipment_id=None,
                route_label="Актау → Баку",
                origin_port_id="port_aktau",
                destination_port_id="port_baku",
                status="underway",
                lat=point_on_path(path_for("port_aktau", "port_baku"), 0.45)[0],
                lon=point_on_path(path_for("port_aktau", "port_baku"), 0.45)[1],
                heading_deg=point_on_path(path_for("port_aktau", "port_baku"), 0.45)[2],
                speed_knots=13.0,
                progress=0.45,
                updated_at=now,
            ),
            Vessel(
                id="ves_makh_liner",
                name="Derbent Wave",
                mmsi="273445880",
                shipment_id=None,
                route_label="Махачкала → Энзели",
                origin_port_id="port_makhachkala",
                destination_port_id="port_anzali",
                status="underway",
                lat=point_on_path(path_for("port_makhachkala", "port_anzali"), 0.55)[0],
                lon=point_on_path(path_for("port_makhachkala", "port_anzali"), 0.55)[1],
                heading_deg=point_on_path(path_for("port_makhachkala", "port_anzali"), 0.55)[2],
                speed_knots=10.2,
                progress=0.55,
                updated_at=now,
            ),
            Vessel(
                id="ves_port_idle",
                name="Volga Trader",
                mmsi="273201010",
                shipment_id="shp_sct_2039",
                route_label="Актау (на рейде)",
                origin_port_id="port_aktau",
                destination_port_id="port_aktau",
                status="anchored",
                lat=43.62,
                lon=51.12,
                heading_deg=90,
                speed_knots=0.2,
                progress=1.0,
                updated_at=now,
            ),
        ]
        session.add_all(vessels)
        await session.commit()

    # Always keep a fresh storm/wind forecast set for the alert engine
    fx_count = len((await session.execute(select(WeatherForecast))).scalars().all())
    if fx_count < 3:
        session.add_all(
            [
                WeatherForecast(
                    id=f"wx_{uuid.uuid4().hex[:8]}",
                    port_id="port_astrakhan",
                    forecast_for=now + timedelta(hours=6),
                    available_at=now,
                    severity_index=0.88,
                    wind_ms=18.5,
                ),
                WeatherForecast(
                    id=f"wx_{uuid.uuid4().hex[:8]}",
                    port_id="port_makhachkala",
                    forecast_for=now + timedelta(hours=12),
                    available_at=now,
                    severity_index=0.62,
                    wind_ms=14.0,
                ),
                WeatherForecast(
                    id=f"wx_{uuid.uuid4().hex[:8]}",
                    port_id="port_anzali",
                    forecast_for=now + timedelta(hours=18),
                    available_at=now,
                    severity_index=0.35,
                    wind_ms=8.0,
                ),
                WeatherForecast(
                    id=f"wx_{uuid.uuid4().hex[:8]}",
                    port_id="port_aktau",
                    forecast_for=now + timedelta(hours=9),
                    available_at=now,
                    severity_index=0.72,
                    wind_ms=15.5,
                ),
            ]
        )
        await session.commit()

    if not get_cells():
        advance_storms(dt=0.0, force=True)
    # Refresh alert snapshot from current cells (positions change on paced interval)
    await rebuild_weather_alerts(session)


COMPLETED_SHIPMENT_STATUSES = frozenset({"delivered", "completed", "cancelled"})
# Полный рейс A→B занимает 5 минут реального времени
JOURNEY_WALL_SECONDS = 300.0


def _complete_shipment_arrival(v: Vessel, shipment: Shipment | None) -> None:
    """Vessel reached B: leave map, move shipment to «Завершённые»."""
    v.progress = 1.0
    v.status = "arrived"
    v.speed_knots = 0.0
    v.updated_at = datetime.now(timezone.utc)
    if not shipment:
        return
    shipment.status = "delivered"
    shipment.current_stage = "Завершено"
    shipment.current_location = shipment.route_to
    shipment.missed_connection = False
    shipment.attention_title = None
    shipment.attention_detail = None
    if shipment.predicted_eta is None and shipment.planned_eta is not None:
        shipment.predicted_eta = shipment.planned_eta


def _advance_vessel(
    v: Vessel,
    alternative_id: str | None = None,
    shipment: Shipment | None = None,
) -> None:
    """Move shipment vessel A→B in ~5 wall-clock minutes; complete on arrival."""
    now = datetime.now(timezone.utc)
    # На карте только транспорт, привязанный к перевозке
    if not v.shipment_id or not shipment:
        v.updated_at = now
        return
    if shipment.status in COMPLETED_SHIPMENT_STATUSES:
        v.status = "arrived"
        v.speed_knots = 0.0
        v.progress = 1.0
        v.updated_at = now
        return
    if v.status == "arrived" or float(v.progress or 0) >= 0.98:
        _complete_shipment_arrival(v, shipment)
        return

    # Погрузка / рейд → выходим в рейс
    if v.status in {"anchored", "loading"} or float(v.speed_knots or 0) < 0.5:
        v.status = "underway"
        v.speed_knots = max(float(v.speed_knots or 0), 12.0)
        if float(v.progress or 0) <= 0:
            v.progress = 0.0

    points = path_for(v.origin_port_id, v.destination_port_id, alternative_id)
    if len(points) < 2:
        v.updated_at = now
        return

    last = v.updated_at or now
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    elapsed = (now - last).total_seconds()
    # Не скакать сразу до финиша после простоя; тик UI ~2.5 с
    elapsed = min(max(elapsed, 0.0), 12.0)
    step = elapsed / JOURNEY_WALL_SECONDS
    v.progress = float(v.progress or 0) + step
    if v.progress >= 0.98:
        lat, lon, heading = point_on_path(points, 1.0)
        v.lat, v.lon, v.heading_deg = lat, lon, heading
        _complete_shipment_arrival(v, shipment)
        return
    lat, lon, heading = point_on_path(points, float(v.progress))
    v.lat = lat
    v.lon = lon
    v.heading_deg = heading
    # Скорость для UI: узлы так, будто весь путь = 5 минут
    dist_nm = max(path_length_km(points) / 1.852, 1.0)
    v.speed_knots = round(dist_nm / (JOURNEY_WALL_SECONDS / 3600.0), 1)
    v.updated_at = now
    if shipment.status in {"planned", "delayed", "in_transit"}:
        shipment.status = "in_transit"
        if shipment.current_stage in {"Планирование", "Ж/Д к порту", "Портовая обработка", ""}:
            shipment.current_stage = "Морской переход"


async def tick_tracking(session: AsyncSession, *, hours: float = 0.35) -> dict:
    await ensure_tracking_data(session)
    # Live weather: storms drift at most every ~2.5 minutes
    advance_storms(dt=1.0, force=False)
    vessels = (await session.execute(select(Vessel))).scalars().all()
    shipments = {
        s.id: s
        for s in (await session.execute(select(Shipment))).scalars().all()
    }
    for v in vessels:
        shipment = shipments.get(v.shipment_id) if v.shipment_id else None
        alt = None
        if shipment is not None:
            alt = shipment.selected_alternative_id
        alt = alt or get_alt(v.id)
        _advance_vessel(v, alt, shipment)
    await session.commit()
    await rebuild_weather_alerts(session)
    return await tracking_dashboard(session)


async def rebuild_weather_alerts(session: AsyncSession) -> None:
    """Build alerts from live moving storm cells + vessel proximity."""
    now = datetime.now(timezone.utc)
    old = (await session.execute(select(WeatherAlert))).scalars().all()
    for a in old:
        await session.delete(a)
    await session.flush()

    vessels = (await session.execute(select(Vessel))).scalars().all()
    cells = get_cells()
    if not cells:
        cells = advance_storms(dt=0.0, force=True)

    alerts: list[WeatherAlert] = []
    for cell in cells:
        lat = float(cell["lat"])
        lon = float(cell["lon"])
        severity_idx = float(cell.get("severity") or 0.5)
        wind = float(cell.get("wind_ms") or 10)
        radius = float(cell.get("radius_km") or 70)
        kind = cell.get("kind") or ("storm" if severity_idx >= 0.72 else "wind")
        sev = "high" if severity_idx >= 0.72 else "medium" if severity_idx >= 0.5 else "low"
        if sev == "low":
            continue

        affected: list[str] = []
        for v in vessels:
            if v.status == "anchored":
                continue
            dist = haversine_km(v.lat, v.lon, lat, lon)
            if dist <= radius * 1.2:
                affected.append(v.id)
            else:
                # Ahead on route: destination near cell
                dest = PORT_COORDS.get(v.destination_port_id)
                if dest and haversine_km(dest[0], dest[1], lat, lon) <= radius * 1.3 and v.progress < 0.9:
                    if v.id not in affected:
                        affected.append(v.id)

        drift = math.degrees(math.atan2(float(cell.get("vy") or 0), float(cell.get("vx") or 0.001))) % 360
        title = f"{cell.get('name') or 'Ячейка'} · live"
        detail = (
            f"Ветер {wind:.0f} м/с · радиус ~{radius:.0f} км · "
            f"индекс {severity_idx:.2f} · дрейф {drift:.0f}°. "
            f"Ячейка движется в реальном времени (демо)."
        )
        if affected:
            names = [next(v.name for v in vessels if v.id == i) for i in affected]
            detail += f" Затронуты: {', '.join(names)}."
            detail += " Рекомендация: выбрать альтернативный морской путь."

        alerts.append(
            WeatherAlert(
                id=f"wal_{cell['id']}",
                kind=kind,
                severity=sev,
                title=title,
                detail=detail,
                port_id=None,
                lat=lat,
                lon=lon,
                wind_ms=wind,
                valid_from=now,
                valid_to=now + timedelta(hours=3),
                predicted=True,
                active=True,
                affected_vessel_ids=affected,
            )
        )

    # Per-vessel immediate collision advisory
    for v in vessels:
        if v.status != "underway":
            continue
        hits = cells_affecting(v.lat, v.lon, cells)
        strong = [c for c in hits if float(c.get("severity") or 0) >= 0.65]
        if not strong:
            continue
        c = max(strong, key=lambda x: float(x.get("severity") or 0))
        alerts.append(
            WeatherAlert(
                id=f"wal_route_{v.id}",
                kind="storm",
                severity="high",
                title=f"{v.name}: шторм на курсе",
                detail=(
                    f"Судно в зоне «{c.get('name')}» ({int(v.progress * 100)}% пути). "
                    f"Ветер {float(c['wind_ms']):.0f} м/с. Выберите обход на карте."
                ),
                port_id=v.destination_port_id,
                lat=float(c["lat"]),
                lon=float(c["lon"]),
                wind_ms=float(c["wind_ms"]),
                valid_from=now,
                valid_to=now + timedelta(hours=2),
                predicted=False,
                active=True,
                affected_vessel_ids=[v.id],
            )
        )

    session.add_all(alerts)
    await session.commit()


def _vessel_out(v: Vessel, alternative_id: str | None = None) -> dict:
    points = path_for(v.origin_port_id, v.destination_port_id, alternative_id)
    # Snap reported position onto corridor for consistent UI
    if len(points) >= 2 and v.status != "anchored":
        lat, lon, heading = point_on_path(points, float(v.progress or 0))
    else:
        lat, lon, heading = v.lat, v.lon, v.heading_deg
    xy = vessel_map_xy(v)
    sea_points = path_for(v.origin_port_id, v.destination_port_id, alternative_id, include_ports=False)
    cells = get_cells()
    scored = score_storm_alternatives(v.origin_port_id, v.destination_port_id, cells)
    current_id = alternative_id or "alt_current"
    current_alt = next((a for a in scored if a["id"] == current_id), None)
    route_storm = bool(current_alt and not current_alt.get("storm_safe", True))
    return {
        "id": v.id,
        "name": v.name,
        "mmsi": v.mmsi,
        "shipment_id": v.shipment_id,
        "route_label": v.route_label,
        "origin_port_id": v.origin_port_id,
        "destination_port_id": v.destination_port_id,
        "selected_alternative_id": alternative_id,
        "status": v.status,
        "status_label": {
            "underway": "В пути",
            "anchored": "На рейде",
            "arrived": "Прибыло",
        }.get(v.status, v.status),
        "lat": round(lat, 4),
        "lon": round(lon, 4),
        "heading_deg": round(heading, 1),
        "speed_knots": round(v.speed_knots, 1),
        "progress": round(float(v.progress), 3),
        "progress_pct": int(round(float(v.progress) * 100)),
        "route_path": [{"lat": p[0], "lon": p[1]} for p in points],
        "waypoints": [{"lat": p[0], "lon": p[1]} for p in sea_points],
        "storm_alternatives": scored,
        "route_storm_danger": route_storm,
        "map": xy,
        "updated_at": v.updated_at,
        "updated_label": _msk_label(v.updated_at),
        "data_quality": v.data_quality,
    }


def _alert_out(a: WeatherAlert) -> dict:
    return {
        "id": a.id,
        "kind": a.kind,
        "severity": a.severity,
        "title": a.title,
        "detail": a.detail,
        "port_id": a.port_id,
        "lat": a.lat,
        "lon": a.lon,
        "map": project_to_map(a.lat, a.lon, a.port_id),
        "wind_ms": a.wind_ms,
        "radius_km": None,
        "valid_from": a.valid_from,
        "valid_to": a.valid_to,
        "valid_label": f"{_msk_label(a.valid_from)} → {_msk_label(a.valid_to)}",
        "predicted": a.predicted,
        "active": a.active,
        "live": True,
        "affected_vessel_ids": a.affected_vessel_ids or [],
        "data_quality": a.data_quality,
    }


async def tracking_dashboard(session: AsyncSession) -> dict:
    await ensure_tracking_data(session)
    if not get_cells():
        advance_storms(dt=0.0, force=True)
    vessels = (await session.execute(select(Vessel).order_by(Vessel.name))).scalars().all()
    shipments = {
        s.id: s for s in (await session.execute(select(Shipment))).scalars().all()
    }
    alerts = (
        await session.execute(
            select(WeatherAlert).where(WeatherAlert.active.is_(True)).order_by(WeatherAlert.severity.desc())
        )
    ).scalars().all()
    # severity sort fallback
    order = {"high": 0, "medium": 1, "low": 2}
    alerts = sorted(alerts, key=lambda a: order.get(a.severity, 9))

    ports = (await session.execute(select(Port))).scalars().all()
    port_markers = [
        {
            "id": p.id,
            "name": (p.name or p.id).replace(" (демо)", ""),
            "lat": p.lat,
            "lon": p.lon,
            "kind": "city",
            "map": project_to_map(p.lat, p.lon, p.id),
        }
        for p in ports
    ]

    # На карте — только суда активных перевозок (A→B), без завершённых и «сирот»
    map_vessels: list[Vessel] = []
    for v in vessels:
        if not v.shipment_id:
            continue
        shipment = shipments.get(v.shipment_id)
        if shipment is None or shipment.status in COMPLETED_SHIPMENT_STATUSES:
            continue
        if v.status == "arrived" or float(v.progress or 0) >= 0.98:
            continue
        map_vessels.append(v)

    vessel_payload = []
    for v in map_vessels:
        alt = None
        if v.shipment_id and v.shipment_id in shipments:
            alt = shipments[v.shipment_id].selected_alternative_id
        alt = alt or get_alt(v.id)
        vessel_payload.append(_vessel_out(v, alt))

    # Corridor catalog for map drawing — по одной схеме на активный груз
    corridors = []
    seen = set()
    for v in vessel_payload:
        key = (v["id"], v["origin_port_id"], v["destination_port_id"], v.get("selected_alternative_id"))
        if key in seen:
            continue
        seen.add(key)
        corridors.append(
            {
                "id": f"ship_{v['id']}",
                "shipment_id": v.get("shipment_id"),
                "origin_port_id": key[1],
                "destination_port_id": key[2],
                "alternative_id": key[3],
                "path": v["route_path"],
                "waypoints": v["waypoints"],
            }
        )

    map_ids = {v["id"] for v in vessel_payload}
    high = sum(1 for a in alerts if a.severity == "high")
    storm_affected = sorted(
        {
            vid
            for a in alerts
            if a.severity == "high"
            for vid in (a.affected_vessel_ids or [])
            if vid in map_ids
        }
        | {v["id"] for v in vessel_payload if v.get("route_storm_danger")}
    )
    cells = get_cells()
    storm_cells = [
        {
            "id": c["id"],
            "name": c.get("name") or c["id"],
            "lat": float(c["lat"]),
            "lon": float(c["lon"]),
            "wind_ms": float(c.get("wind_ms") or 0),
            "severity": float(c.get("severity") or 0),
            "radius_km": float(c.get("radius_km") or 70),
            "kind": c.get("kind") or "storm",
            "heading_deg": round(
                (math.degrees(math.atan2(float(c.get("vy") or 0), float(c.get("vx") or 0.001))) + 360) % 360,
                1,
            ),
            "live": True,
        }
        for c in cells
    ]
    return {
        "title": "GPS-трекер судов · Каспий",
        "subtitle": "На карте только суда активных перевозок · A → B",
        "refreshed_at": datetime.now(timezone.utc),
        "kpis": {
            "vessels": len(vessel_payload),
            "underway": sum(1 for v in vessel_payload if v["status"] == "underway"),
            "alerts": len(alerts),
            "storm_alerts": high,
        },
        "vessels": vessel_payload,
        "alerts": [_alert_out(a) for a in alerts],
        "storm_cells": storm_cells,
        "ports": port_markers,
        "corridors": corridors,
        "storm_affected_vessel_ids": storm_affected,
        "disclaimer": (
            "GPS судов и прогноз штормовых ячеек на Каспии. "
            "Обновление карты в реальном времени."
        ),
        "data_quality": "operational",
    }


async def select_vessel_route(session: AsyncSession, vessel_id: str, alternative_id: str) -> dict:
    """Choose storm bypass corridor for a vessel (and linked shipment if any)."""
    await ensure_tracking_data(session)
    v = (
        await session.execute(select(Vessel).where(Vessel.id == vessel_id))
    ).scalar_one_or_none()
    if not v:
        raise ValueError("Vessel not found")

    scored = score_storm_alternatives(v.origin_port_id, v.destination_port_id, get_cells())
    chosen = next((a for a in scored if a["id"] == alternative_id), None)
    if not chosen:
        # Fallback to unscored catalog (UI may send before storms load)
        alts = storm_alternatives_for_pair(v.origin_port_id, v.destination_port_id)
        chosen = next((a for a in alts if a["id"] == alternative_id), None)
    if not chosen:
        raise ValueError("Unknown alternative_id for this route")
    if not chosen.get("feasible", True):
        raise ValueError("Alternative not feasible")

    persist_alt = None if alternative_id == "alt_current" else alternative_id
    set_alt(v.id, persist_alt)

    shipment: Shipment | None = None
    if v.shipment_id:
        shipment = (
            await session.execute(
                select(Shipment)
                .where(Shipment.id == v.shipment_id)
                .options(selectinload(Shipment.legs))
            )
        ).scalar_one_or_none()
        if shipment:
            # Always persist sea corridor choice so next tick follows the new path
            shipment.selected_alternative_id = persist_alt
            shipment.missed_connection = False
            try:
                from app.services.alternatives import apply_alternative, build_alternatives

                built = await build_alternatives(session, shipment.id)
                ship_alt = next(
                    (a for a in built["alternatives"] if a["id"] == alternative_id),
                    None,
                )
                if ship_alt and ship_alt.get("feasible"):
                    await apply_alternative(session, shipment, ship_alt)
            except Exception:
                # Sea-route alts may not exist in shipment catalog — path switch still applies
                pass
            shipment.selected_alternative_id = persist_alt
            if persist_alt:
                shipment.attention_title = "Маршрут изменён"
                shipment.attention_detail = (
                    f"Выбран безопасный коридор: {chosen.get('title') or persist_alt}"
                )
                if shipment.status in {"planned", "delayed", "in_transit"}:
                    shipment.status = "in_transit"
                    if not (shipment.current_stage or "").startswith("Морской"):
                        shipment.current_stage = "Морской переход · обход шторма"
            else:
                shipment.attention_title = None
                shipment.attention_detail = None

    points = path_for(v.origin_port_id, v.destination_port_id, persist_alt)
    if len(points) >= 2:
        if v.status == "arrived" or float(v.progress or 0) >= 0.95:
            v.progress = min(float(v.progress or 0.35), 0.85)
        if v.status in {"anchored", "loading", "arrived"}:
            v.status = "underway"
        if v.status == "underway":
            v.speed_knots = max(float(v.speed_knots or 0), 12.0)
        # Keep progress; snap onto the new corridor so the ship visibly switches path
        lat, lon, heading = point_on_path(points, float(v.progress or 0.0))
        v.lat, v.lon, v.heading_deg = lat, lon, heading
        names = {
            "port_astrakhan": "Астрахань",
            "port_makhachkala": "Махачкала",
            "port_aktau": "Актау",
            "port_baku": "Баку",
            "port_anzali": "Энзели",
        }
        if persist_alt is None:
            v.route_label = (
                f"{names.get(v.origin_port_id, v.origin_port_id)} → "
                f"{names.get(v.destination_port_id, v.destination_port_id)}"
            )
        else:
            v.route_label = str(chosen.get("title") or persist_alt)
        v.updated_at = datetime.now(timezone.utc)

    await session.commit()
    return await tracking_dashboard(session)
