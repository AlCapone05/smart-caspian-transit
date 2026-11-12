"""Route alternatives + apply selection (synthetic demo)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Event, Shipment, TransportLeg, Vessel
from app.services.sea_routes import point_on_path, path_for

MSK = ZoneInfo("Europe/Moscow")


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _msk_label(dt: datetime | None) -> str | None:
    if not dt:
        return None
    local = _aware(dt).astimezone(MSK)
    months = {
        1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
        7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек",
    }
    return f"{local.day} {months[local.month]}, {local.strftime('%H:%M')}"


def _duration_label(hours: float) -> str:
    days = int(hours // 24)
    h = int(round(hours % 24))
    return f"{days} д {h:02d} ч"


def _money(v: float, delta_pct: int | None = None) -> str:
    base = f"{int(v):,}".replace(",", " ") + " ₽"
    if delta_pct:
        return f"{base} · +{delta_pct}%"
    return base


async def build_alternatives(session: AsyncSession, shipment_id: str) -> dict:
    result = await session.execute(
        select(Shipment)
        .where((Shipment.id == shipment_id) | (Shipment.reference == shipment_id))
        .options(selectinload(Shipment.legs))
    )
    shipment = result.scalar_one()
    planned = _aware(shipment.planned_eta)
    predicted = _aware(shipment.predicted_eta or shipment.planned_eta)
    delay = float(shipment.delay_hours or 0)
    base_cost = float(shipment.cost_rub or 180000)
    base_co2 = float(shipment.co2e_tonnes or 1.84)
    origin = shipment.route_from or "порт отправления"
    selected = shipment.selected_alternative_id

    start = datetime(2026, 11, 13, 8, 0, tzinfo=MSK).astimezone(timezone.utc)
    current_hours = max(1.0, (predicted - start).total_seconds() / 3600)

    via_makh_eta = predicted - timedelta(hours=12)
    via_makh_delay = max(0.0, delay - 12)
    via_makh_hours = max(1.0, current_hours - 12)
    via_makh_cost = round(base_cost * 1.08)
    via_makh_co2 = round(base_co2 * 1.10, 2)

    via_aktau_eta = predicted - timedelta(hours=14)
    via_aktau_delay = max(0.0, delay - 14)
    via_aktau_hours = max(1.0, current_hours - 14)
    via_aktau_cost = round(base_cost * 1.15)
    via_aktau_co2 = round(base_co2 * 1.17, 2)

    alternatives = [
        {
            "id": "alt_current",
            "title": "Текущий маршрут",
            "subtitle": f"Прямой рейс из {origin}",
            "feasible": True,
            "is_current": selected in (None, "alt_current"),
            "recommended": False,
            "eta": predicted,
            "eta_label": _msk_label(predicted),
            "delay_hours": delay,
            "delay_label": f"+{int(delay)} часов" if delay else "По плану",
            "total_hours": round(current_hours, 1),
            "duration_label": _duration_label(current_hours),
            "cost_rub": base_cost,
            "cost_label": _money(base_cost),
            "cost_delta_pct": None,
            "transfers": 2,
            "co2e_tonnes": base_co2,
            "co2e_label": f"{base_co2:.2f} т".replace(".", ","),
            "co2e_delta_pct": None,
            "constraints": "Погода и очередь" if delay else "Без критических ограничений",
            "availability": "Место удерживается",
            "action_label": "Текущий маршрут",
            "description": f"Базовый план {shipment.route_from} → {shipment.route_to}.",
            "assumptions": ["Демо-тариф ₽", "CO₂e ±20%", "Не официальное расписание"],
            "infeasible_reason": None,
            "service_id": None,
        },
        {
            "id": "alt_via_makhachkala",
            "title": "Через Махачкалу",
            "subtitle": "Самое раннее прибытие",
            "feasible": True,
            "is_current": selected == "alt_via_makhachkala",
            "recommended": True,
            "eta": via_makh_eta,
            "eta_label": _msk_label(via_makh_eta),
            "delay_hours": via_makh_delay,
            "delay_label": f"+{int(via_makh_delay)} часов" if via_makh_delay else "По плану",
            "total_hours": round(via_makh_hours, 1),
            "duration_label": _duration_label(via_makh_hours),
            "cost_rub": via_makh_cost,
            "cost_label": _money(via_makh_cost, 8),
            "cost_delta_pct": 8,
            "transfers": 3,
            "co2e_tonnes": via_makh_co2,
            "co2e_label": f"{via_makh_co2:.2f} т · +10%".replace(".", ","),
            "co2e_delta_pct": 10,
            "constraints": "Автоплечо 430 км",
            "availability": "2 места · до 12:00",
            "action_label": "Выбрать маршрут" if selected != "alt_via_makhachkala" else "Выбран",
            "description": "Через Махачкалу: более раннее прибытие, доп. перегрузка.",
            "assumptions": ["Демо-слот Махачкала–Энзели", "Демо-тариф ₽", "CO₂e ±20%"],
            "infeasible_reason": None,
            "service_id": "svc_makh_anz_01",
            "origin_port_id": "port_makhachkala",
        },
        {
            "id": "alt_via_aktau",
            "title": "Через Актау",
            "subtitle": "Штормовой восточный обход",
            "feasible": True,
            "is_current": selected == "alt_via_aktau",
            "recommended": False,
            "eta": via_aktau_eta,
            "eta_label": (_msk_label(via_aktau_eta) or "") + "*",
            "delay_hours": via_aktau_delay,
            "delay_label": f"+{int(via_aktau_delay)} часа*",
            "total_hours": round(via_aktau_hours, 1),
            "duration_label": _duration_label(via_aktau_hours) + "*",
            "cost_rub": via_aktau_cost,
            "cost_label": _money(via_aktau_cost, 15),
            "cost_delta_pct": 15,
            "transfers": 3,
            "co2e_tonnes": via_aktau_co2,
            "co2e_label": f"{via_aktau_co2:.2f} т · +17%".replace(".", ","),
            "co2e_delta_pct": 17,
            "constraints": "Длиннее по мили, обходит западный шторм",
            "availability": "1 место · демо",
            "action_label": "Выбрать обход" if selected != "alt_via_aktau" else "Выбран",
            "description": "Восточный морской обход через Актау при сильном шторме на прямом пути.",
            "assumptions": ["Демо-коридор Каспия", "Демо-тариф ₽", "CO₂e ±20%"],
            "infeasible_reason": None,
            "service_id": "svc_aktau_anz_01",
            "origin_port_id": "port_aktau",
        },
    ]

    insight = {
        "title": "На 12 часов быстрее, стоимость выше на 8%",
        "detail": (
            f"Для {shipment.reference}: через Махачкалу раньше на 12 ч, "
            f"+8% к стоимости и +10% CO₂e относительно текущего плана."
        ),
    }

    return {
        "shipment_id": shipment.id,
        "reference": shipment.reference,
        "route_label": f"{shipment.route_from} → {shipment.route_to}",
        "insight": insight,
        "alternatives": alternatives,
        "infeasible_reason": None,
        "footnote": (
            "¹ От отправления 13 ноября, 08:00 МСК.  * Расчётное время при наличии мест; "
            "вариант нельзя выбрать. Источник: модель SCT и тестовые данные перевозчиков. "
            "Оценка CO₂e: ±20%."
        ),
        "co2_disclaimer": "Оценка CO₂e приближённая; единицы т CO₂e; ±20%.",
        "data_quality": "synthetic_demo",
        "planned_eta": planned,
    }


async def apply_alternative(
    session: AsyncSession,
    shipment: Shipment,
    chosen: dict,
) -> Shipment:
    """Persist route choice onto shipment + visible legs."""
    now = datetime.now(timezone.utc)
    shipment.selected_alternative_id = chosen["id"]
    if chosen.get("eta"):
        shipment.predicted_eta = chosen["eta"]
    if chosen.get("delay_hours") is not None:
        shipment.delay_hours = float(chosen["delay_hours"])
    if chosen.get("cost_rub") is not None:
        shipment.cost_rub = float(chosen["cost_rub"])
    if chosen.get("co2e_tonnes") is not None:
        shipment.co2e_tonnes = float(chosen["co2e_tonnes"])
    shipment.risk_level = "medium" if shipment.delay_hours < 24 else "high"
    shipment.missed_connection = False if shipment.delay_hours < 12 else shipment.missed_connection
    shipment.risk_headline = f"Выбран маршрут: {chosen['title']}"
    shipment.risk_detail = chosen.get("description") or chosen.get("subtitle")
    shipment.attention_title = (
        f"{shipment.reference} · {chosen['title']}"
        if shipment.delay_hours > 0
        else f"{shipment.reference} · маршрут обновлён"
    )
    shipment.attention_detail = chosen.get("subtitle")
    if chosen["id"] == "alt_via_makhachkala":
        shipment.current_stage = "Перенаправление через Махачкалу"
        shipment.current_location = "переход на порт Махачкала (демо)"
    elif chosen["id"] == "alt_via_aktau":
        shipment.current_stage = "Восточный обход через Актау"
        shipment.current_location = "морской обход (демо)"
    elif chosen["id"] == "alt_east_bypass":
        shipment.current_stage = "Восточный обход шторма"
        shipment.current_location = "открытое море (демо)"
    elif chosen["id"] == "alt_current":
        shipment.current_stage = shipment.current_stage or "В пути"
        shipment.risk_headline = "Прямой маршрут восстановлен"

    # Reroute linked vessels onto storm-bypass corridor
    vessels = (
        await session.execute(select(Vessel).where(Vessel.shipment_id == shipment.id))
    ).scalars().all()
    for v in vessels:
        if v.status == "anchored":
            continue
        points = path_for(v.origin_port_id, v.destination_port_id, chosen["id"])
        if len(points) >= 2:
            lat, lon, heading = point_on_path(points, float(v.progress or 0.3))
            v.lat = lat
            v.lon = lon
            v.heading_deg = heading
            if v.status == "arrived":
                v.status = "underway"
                v.speed_knots = max(v.speed_knots, 10.0)
                v.progress = min(0.85, float(v.progress or 0.4))
            if chosen["id"] == "alt_via_makhachkala":
                v.route_label = f"{shipment.route_from} → Махачкала → {shipment.route_to}"
            elif chosen["id"] == "alt_via_aktau":
                v.route_label = f"{shipment.route_from} → Актау → {shipment.route_to}"
            elif chosen["id"] == "alt_current":
                v.route_label = f"{shipment.route_from} → {shipment.route_to}"

    # Update sea / last active leg labels for UI
    legs = sorted(shipment.legs, key=lambda x: x.sequence)
    sea = next((l for l in legs if l.mode == "sea"), None)
    if sea and chosen.get("service_id"):
        sea.scheduled_service_id = chosen["service_id"]
        if chosen.get("origin_port_id"):
            sea.origin_port_id = chosen["origin_port_id"]
            sea.origin_name = "Махачкала" if "makh" in chosen["id"] else sea.origin_name
        if chosen.get("eta"):
            sea.predicted_arrival = chosen["eta"] - timedelta(hours=14)
            sea.predicted_departure = sea.predicted_arrival - timedelta(hours=22)
        sea.status = "rebooked"
        sea.stage_status_label = "↻ Перебронирован"
        sea.label = "Море · альтернатива"

    # If no sea leg, shift last leg ETA
    if not sea and legs and chosen.get("eta"):
        last = legs[-1]
        last.predicted_arrival = chosen["eta"]
        last.status = "rebooked"
        last.stage_status_label = "↻ План обновлён"

    session.add(
        Event(
            id=f"evt_{uuid.uuid4().hex[:10]}",
            shipment_id=shipment.id,
            event_type="alternative_selected",
            title=f"Выбран маршрут: {chosen['title']}",
            occurred_at=now,
            available_at=now,
            payload={
                "alternative_id": chosen["id"],
                "title": chosen["title"],
                "eta": chosen.get("eta_label"),
                "cost_rub": chosen.get("cost_rub"),
            },
            source="api",
        )
    )
    return shipment
