"""Create / update / delete shipments for dispatcher CRUD."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Document,
    DocumentStatusHistory,
    Event,
    Prediction,
    Shipment,
    TransportLeg,
    Vessel,
)
from app.services.documents import DISCLAIMER, PACKAGE_TYPES, ensure_package_docs
from app.services.sea_routes import (
    path_for,
    path_length_km,
    point_on_path,
    port_label,
    resolve_port_id,
)
from app.services.serialize import shipment_detail, shipment_summary

MSK_OFFSET = timezone.utc

STAGES = (
    "Планирование",
    "Ж/Д к порту",
    "Портовая обработка",
    "Морской переход",
    "Выгрузка",
    "Автодоставка",
    "Завершено",
)


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _parse_dt(value: str | datetime | None, fallback: datetime) -> datetime:
    if value is None:
        return fallback
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    raw = str(value).strip()
    if not raw:
        return fallback
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _container_no(reference: str) -> str:
    return f"MSCU{uuid.uuid4().hex[:7].upper()}"


def _estimate_cost_co2(sea_km: float, tonnes: float) -> tuple[float, float]:
    sea = max(sea_km, 200.0)
    cost = 95000 + sea * 95 + tonnes * 1800
    co2 = max(0.6, sea * 0.0018 + tonnes * 0.012)
    return round(cost, 0), round(co2, 2)


def _build_default_legs(
    *,
    shipment_id: str,
    origin_port: str,
    dest_port: str,
    route_from: str,
    route_to: str,
    planned: datetime,
    predicted: datetime,
    sea_km: float,
    stage: str,
) -> list[TransportLeg]:
    # Timeline anchors relative to planned ETA (hours before arrival)
    specs = [
        (1, "rail", "Железная дорога", route_from, f"Порт {route_from}", origin_port, origin_port, 45.0, 110, 98),
        (
            2,
            "port_handling",
            "Порт отправления",
            f"{route_from} · приём",
            f"{route_from} · погрузка",
            origin_port,
            origin_port,
            8.0,
            98,
            86,
        ),
        (3, "sea", "Море", route_from, route_to, origin_port, dest_port, max(sea_km, 1.0), 86, 24),
        (
            4,
            "port_handling",
            "Порт назначения",
            f"{route_to} · выгрузка",
            f"{route_to} · выдача",
            dest_port,
            dest_port,
            8.0,
            24,
            12,
        ),
        (5, "road", "Автодоставка", route_to, "Склад получателя", dest_port, dest_port, 120.0, 12, 0),
    ]

    stage_idx = 0
    for i, name in enumerate(STAGES):
        if name.lower() in stage.lower() or stage.lower() in name.lower():
            stage_idx = min(i, 4)
            break
    if "мор" in stage.lower():
        stage_idx = 2
    elif "порт" in stage.lower() and "назн" in stage.lower():
        stage_idx = 3
    elif "авто" in stage.lower() or "заверш" in stage.lower():
        stage_idx = 4

    legs: list[TransportLeg] = []
    for seq, mode, label, o, d, op, dp, dist, h0, h1 in specs:
        if seq - 1 < stage_idx:
            status, badge = "completed", "✓ Пройдено"
        elif seq - 1 == stage_idx:
            status, badge = "in_progress", "◉ В работе"
        else:
            status, badge = "planned", "○ Далее"
        legs.append(
            TransportLeg(
                id=_uid("leg"),
                shipment_id=shipment_id,
                sequence=seq,
                mode=mode,
                label=label,
                origin_name=o,
                destination_name=d,
                origin_port_id=op,
                destination_port_id=dp,
                distance_km=dist,
                planned_departure=planned - timedelta(hours=h0),
                planned_arrival=planned - timedelta(hours=h1),
                predicted_departure=predicted - timedelta(hours=h0),
                predicted_arrival=predicted - timedelta(hours=h1),
                status=status,
                stage_status_label=badge,
                data_quality="synthetic_demo",
            )
        )
    return legs


def _legs_from_body(
    shipment_id: str,
    raw_legs: list,
    planned: datetime,
    predicted: datetime,
) -> list[TransportLeg]:
    out: list[TransportLeg] = []
    for i, raw in enumerate(raw_legs):
        planned_dep = _parse_dt(raw.get("planned_departure"), planned - timedelta(hours=24 * (len(raw_legs) - i)))
        planned_arr = _parse_dt(raw.get("planned_arrival"), planned - timedelta(hours=24 * (len(raw_legs) - i - 1)))
        out.append(
            TransportLeg(
                id=raw.get("id") or _uid("leg"),
                shipment_id=shipment_id,
                sequence=int(raw.get("sequence") or i + 1),
                mode=(raw.get("mode") or "road").strip(),
                label=(raw.get("label") or raw.get("mode") or "Плечо").strip(),
                origin_name=(raw.get("origin_name") or "").strip() or "—",
                destination_name=(raw.get("destination_name") or "").strip() or "—",
                origin_port_id=raw.get("origin_port_id"),
                destination_port_id=raw.get("destination_port_id"),
                distance_km=float(raw.get("distance_km") or 0),
                planned_departure=planned_dep,
                planned_arrival=planned_arr,
                predicted_departure=_parse_dt(raw.get("predicted_departure"), planned_dep),
                predicted_arrival=_parse_dt(raw.get("predicted_arrival"), planned_arr),
                status=(raw.get("status") or "planned").strip(),
                stage_status_label=(raw.get("stage_status_label") or "").strip(),
                data_quality="synthetic_demo",
            )
        )
    return out


async def create_shipment(session: AsyncSession, body: dict) -> dict:
    now = datetime.now(timezone.utc)
    reference = (body.get("reference") or "").strip() or f"SCT-{uuid.uuid4().hex[:4].upper()}"
    exists = (
        await session.execute(select(Shipment).where(Shipment.reference == reference))
    ).scalar_one_or_none()
    if exists:
        raise ValueError(f"Референс уже существует: {reference}")

    origin_port = resolve_port_id(body.get("origin_port_id") or body.get("route_from"), "port_astrakhan")
    dest_port = resolve_port_id(body.get("destination_port_id") or body.get("route_to"), "port_anzali")
    if origin_port == dest_port:
        raise ValueError("Пункт отправления и назначения должны отличаться")

    route_from = (body.get("route_from") or port_label(origin_port)).strip()
    route_to = (body.get("route_to") or port_label(dest_port)).strip()
    # Prefer canonical city labels when ports known
    if not body.get("route_from"):
        route_from = port_label(origin_port)
    if not body.get("route_to"):
        route_to = port_label(dest_port)

    planned = _parse_dt(body.get("planned_eta"), now + timedelta(days=5))
    predicted = _parse_dt(body.get("predicted_eta"), planned)
    if predicted < planned:
        predicted = planned
    delay = float(body.get("delay_hours") if body.get("delay_hours") is not None else max(
        0.0, (predicted - planned).total_seconds() / 3600
    ))

    tonnes = float(body.get("cargo_tonnes") or 20.0)
    sea_path = path_for(origin_port, dest_port, include_ports=False) or path_for(origin_port, dest_port)
    sea_km = path_length_km(sea_path) if sea_path else 700.0
    est_cost, est_co2 = _estimate_cost_co2(sea_km, tonnes)
    cost = float(body["cost_rub"]) if body.get("cost_rub") not in (None, "") else est_cost
    co2 = float(body["co2e_tonnes"]) if body.get("co2e_tonnes") not in (None, "") else est_co2

    risk_level = (body.get("risk_level") or "low").strip()
    status = (body.get("status") or "planned").strip()
    stage = (body.get("current_stage") or "Планирование").strip()
    container = (body.get("container_no") or "").strip() or _container_no(reference)

    risk_headline = body.get("risk_headline")
    risk_detail = body.get("risk_detail")
    attention_title = body.get("attention_title")
    attention_detail = body.get("attention_detail")
    if risk_level == "high" and not risk_headline:
        risk_headline = f"△ Высокий риск · {reference}"
        risk_detail = risk_detail or "Требует контроля стыковки и документов."
        attention_title = attention_title or risk_headline
        attention_detail = attention_detail or f"{route_from} → {route_to}"
    elif risk_level == "medium" and not risk_headline:
        risk_headline = f"Риск средний · {reference}"
        risk_detail = risk_detail or "Следить за погодой и портовой очередью."

    shipment = Shipment(
        id=_uid("shp"),
        reference=reference,
        cargo_description=(body.get("cargo_description") or "Контейнерный груз").strip(),
        cargo_tonnes=tonnes,
        container_no=container,
        equipment=(body.get("equipment") or "1 × 40′ HC").strip(),
        route_from=route_from,
        route_to=route_to,
        current_stage=stage,
        current_location=(body.get("current_location") or route_from).strip(),
        attention_title=attention_title,
        attention_detail=attention_detail,
        risk_headline=risk_headline,
        risk_detail=risk_detail,
        cost_rub=cost,
        co2e_tonnes=co2,
        status=status,
        risk_level=risk_level,
        planned_eta=planned,
        predicted_eta=predicted,
        delay_hours=delay,
        missed_connection=bool(body.get("missed_connection") or False),
        selected_alternative_id=None,
        active_scenario=(body.get("active_scenario") or "normal").strip(),
        created_at=now,
        data_quality="synthetic_demo",
    )
    session.add(shipment)

    if isinstance(body.get("legs"), list) and body["legs"]:
        legs = _legs_from_body(shipment.id, body["legs"], planned, predicted)
    else:
        legs = _build_default_legs(
            shipment_id=shipment.id,
            origin_port=origin_port,
            dest_port=dest_port,
            route_from=route_from,
            route_to=route_to,
            planned=planned,
            predicted=predicted,
            sea_km=sea_km,
            stage=stage,
        )
    session.add_all(legs)

    for dtype in PACKAGE_TYPES:
        # Fresh shipment: most docs missing except commercial invoice draft
        status_doc = "submitted" if dtype in ("commercial_invoice", "packing_list") else "missing"
        session.add(
            Document(
                id=_uid("doc"),
                shipment_id=shipment.id,
                document_type=dtype,
                status=status_doc,
                required=True,
                payload={},
                updated_at=now,
                disclaimer=DISCLAIMER,
                data_quality="synthetic_demo",
            )
        )

    session.add(
        Prediction(
            id=_uid("prd"),
            shipment_id=shipment.id,
            model_name="sct_demo_baseline",
            as_of_ts=now,
            predicted_eta=predicted,
            delay_hours=delay,
            missed_connection=False,
            risk_factors=[
                {
                    "code": "created_via_ui",
                    "label": "Создано вручную",
                    "contribution_hours": 0.0,
                    "note": "Базовый демо-прогноз при создании.",
                }
            ],
            mae_hours_holdout=6.0,
            notes="Базовый прогноз при создании перевозки (синтетика).",
            data_quality="synthetic_demo",
        )
    )

    session.add(
        Event(
            id=_uid("evt"),
            shipment_id=shipment.id,
            event_type="shipment_created",
            title=f"Создана перевозка {reference}",
            occurred_at=now,
            available_at=now,
            payload={
                "source": "ui",
                "origin_port_id": origin_port,
                "destination_port_id": dest_port,
                "sea_km": round(sea_km, 1),
            },
            source="api",
            data_quality="synthetic_demo",
        )
    )

    create_vessel = body.get("create_vessel", True)
    if create_vessel is not False:
        # Груз сразу идёт A→B на карте; по прибытии → «Завершённые»
        if stage == "Завершено" or status in {"delivered", "completed"}:
            progress = 1.0
            vessel_status = "arrived"
            speed = 0.0
            shipment.status = "delivered"
            shipment.current_stage = "Завершено"
        else:
            progress = 0.04
            vessel_status = "underway"
            speed = float(body.get("speed_knots") or 12.0)
            if status == "planned":
                shipment.status = "in_transit"
                if stage in {"Планирование", ""}:
                    shipment.current_stage = "Морской переход"

        path = path_for(origin_port, dest_port) or sea_path
        lat, lon, heading = point_on_path(path, progress) if path else (42.0, 50.0, 180.0)

        vessel_name = (body.get("vessel_name") or "").strip() or f"MV {reference}"
        session.add(
            Vessel(
                id=_uid("ves"),
                name=vessel_name,
                mmsi=str(273000000 + int(uuid.uuid4().hex[:6], 16) % 900000),
                shipment_id=shipment.id,
                route_label=f"{route_from} → {route_to}",
                origin_port_id=origin_port,
                destination_port_id=dest_port,
                status=vessel_status,
                lat=lat,
                lon=lon,
                heading_deg=heading,
                speed_knots=speed,
                progress=progress,
                updated_at=now,
                data_quality="synthetic_demo",
            )
        )
        session.add(
            Event(
                id=_uid("evt"),
                shipment_id=shipment.id,
                event_type="vessel_assigned",
                title=f"Судно назначено: {vessel_name}",
                occurred_at=now,
                available_at=now,
                payload={"origin_port_id": origin_port, "destination_port_id": dest_port},
                source="api",
                data_quality="synthetic_demo",
            )
        )

    await session.commit()

    result = await session.execute(
        select(Shipment)
        .where(Shipment.id == shipment.id)
        .options(
            selectinload(Shipment.legs),
            selectinload(Shipment.events),
            selectinload(Shipment.documents),
            selectinload(Shipment.predictions),
        )
    )
    row = result.scalar_one()
    return shipment_detail(row)


async def update_shipment(session: AsyncSession, shipment_id: str, body: dict) -> dict:
    result = await session.execute(
        select(Shipment)
        .where((Shipment.id == shipment_id) | (Shipment.reference == shipment_id))
        .options(
            selectinload(Shipment.legs),
            selectinload(Shipment.events),
            selectinload(Shipment.documents),
            selectinload(Shipment.predictions),
        )
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise ValueError("Shipment not found")

    str_fields = [
        "reference",
        "cargo_description",
        "container_no",
        "equipment",
        "route_from",
        "route_to",
        "current_stage",
        "current_location",
        "attention_title",
        "attention_detail",
        "risk_headline",
        "risk_detail",
        "status",
        "risk_level",
        "active_scenario",
    ]
    for key in str_fields:
        if key in body and body[key] is not None:
            setattr(shipment, key, str(body[key]).strip() if isinstance(body[key], str) else body[key])

    for key in ("cargo_tonnes", "cost_rub", "co2e_tonnes", "delay_hours"):
        if key in body and body[key] is not None:
            setattr(shipment, key, float(body[key]))

    if "missed_connection" in body:
        shipment.missed_connection = bool(body["missed_connection"])
    if "planned_eta" in body:
        shipment.planned_eta = _parse_dt(body["planned_eta"], shipment.planned_eta)
    if "predicted_eta" in body:
        shipment.predicted_eta = _parse_dt(body["predicted_eta"], shipment.predicted_eta or shipment.planned_eta)

    route_changed = "route_from" in body or "route_to" in body or "origin_port_id" in body or "destination_port_id" in body
    origin_port = resolve_port_id(body.get("origin_port_id") or shipment.route_from, "port_astrakhan")
    dest_port = resolve_port_id(body.get("destination_port_id") or shipment.route_to, "port_anzali")

    # Optional legs replace
    if isinstance(body.get("legs"), list) and body["legs"]:
        for leg in list(shipment.legs):
            await session.delete(leg)
        await session.flush()
        for leg in _legs_from_body(shipment.id, body["legs"], shipment.planned_eta, shipment.predicted_eta or shipment.planned_eta):
            session.add(leg)

    # Keep linked vessel corridor in sync when route changes
    if route_changed:
        vessels = (
            await session.execute(select(Vessel).where(Vessel.shipment_id == shipment.id))
        ).scalars().all()
        for v in vessels:
            v.origin_port_id = origin_port
            v.destination_port_id = dest_port
            v.route_label = f"{shipment.route_from} → {shipment.route_to}"
            path = path_for(origin_port, dest_port)
            if path:
                lat, lon, heading = point_on_path(path, v.progress or 0.1)
                v.lat, v.lon, v.heading_deg = lat, lon, heading
            v.updated_at = datetime.now(timezone.utc)

    await ensure_package_docs(session, shipment)
    session.add(
        Event(
            id=_uid("evt"),
            shipment_id=shipment.id,
            event_type="shipment_updated",
            title=f"Перевозка обновлена: {shipment.reference}",
            occurred_at=datetime.now(timezone.utc),
            available_at=datetime.now(timezone.utc),
            payload={"fields": list(body.keys())},
            source="api",
            data_quality="synthetic_demo",
        )
    )
    await session.commit()

    result = await session.execute(
        select(Shipment)
        .where(Shipment.id == shipment.id)
        .options(
            selectinload(Shipment.legs),
            selectinload(Shipment.events),
            selectinload(Shipment.documents),
            selectinload(Shipment.predictions),
        )
    )
    return shipment_detail(result.scalar_one())


async def delete_shipment(session: AsyncSession, shipment_id: str) -> dict:
    result = await session.execute(
        select(Shipment)
        .where((Shipment.id == shipment_id) | (Shipment.reference == shipment_id))
        .options(selectinload(Shipment.documents).selectinload(Document.history))
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise ValueError("Shipment not found")

    sid = shipment.id
    ref = shipment.reference

    # Unlink vessels
    vessels = (await session.execute(select(Vessel).where(Vessel.shipment_id == sid))).scalars().all()
    for v in vessels:
        v.shipment_id = None

    # Delete children
    docs = (await session.execute(select(Document).where(Document.shipment_id == sid))).scalars().all()
    for d in docs:
        hist = (
            await session.execute(select(DocumentStatusHistory).where(DocumentStatusHistory.document_id == d.id))
        ).scalars().all()
        for h in hist:
            await session.delete(h)
        await session.delete(d)

    for model in (Event, Prediction, TransportLeg):
        rows = (await session.execute(select(model).where(model.shipment_id == sid))).scalars().all()
        for row in rows:
            await session.delete(row)

    await session.delete(shipment)
    await session.commit()
    return {"ok": True, "deleted_id": sid, "reference": ref, "data_quality": "synthetic_demo"}


async def list_for_compare(session: AsyncSession, ids: list[str]) -> list[dict]:
    rows = (
        await session.execute(
            select(Shipment).options(selectinload(Shipment.documents)).order_by(Shipment.reference)
        )
    ).scalars().all()
    if ids:
        wanted = set(ids)
        rows = [s for s in rows if s.id in wanted or s.reference in wanted]
    return [shipment_summary(s) for s in rows]
