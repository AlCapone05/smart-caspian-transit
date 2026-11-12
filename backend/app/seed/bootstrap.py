"""Seed demo data aligned with Figma dispatcher screens (synthetic)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Document,
    DocumentStatusHistory,
    Event,
    Port,
    ScheduledService,
    Shipment,
    TransportLeg,
    WeatherForecast,
)
from app.services.prediction import evaluate_models

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
MSK = ZoneInfo("Europe/Moscow")


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def msk(y, m, d, hh, mm=0) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=MSK).astimezone(timezone.utc)


async def repair_demo_docs(session: AsyncSession) -> None:
    """Patch older DBs so every shipment has a fixable 5-doc package."""
    from app.services.documents import ensure_package_docs

    rows = (
        await session.execute(select(Shipment).options(selectinload(Shipment.documents)))
    ).scalars().all()
    now = datetime.now(timezone.utc)
    for s in rows:
        await ensure_package_docs(session, s)
        by_type = {d.document_type: d for d in s.documents}
        # Legacy HS declaration is optional; package uses certificate_of_origin + insurance
        hs = by_type.get("hs_code_declaration")
        if hs:
            hs.required = False
        # SCT-2051: make cert incomplete (fixable) instead of dead missing-only path
        if s.reference == "SCT-2051":
            cert = by_type.get("certificate_of_origin")
            if cert and cert.status == "missing":
                cert.status = "incomplete"
                cert.updated_at = now
    await session.commit()


async def seed_if_empty(session: AsyncSession) -> None:
    existing = (await session.execute(select(Shipment).limit(1))).scalar_one_or_none()
    if existing:
        await repair_demo_docs(session)
        from app.services.tracking import ensure_tracking_data

        await ensure_tracking_data(session)
        evaluate_models()
        return

    DATA.mkdir(parents=True, exist_ok=True)
    _write_history_csv()

    now = msk(2026, 11, 12, 10, 42)

    ports = [
        Port(id="port_astrakhan", name="Астрахань (демо)", country="RU", timezone="Europe/Moscow", lat=46.35, lon=48.04, handling_norm_hours=12),
        Port(id="port_makhachkala", name="Махачкала (демо)", country="RU", timezone="Europe/Moscow", lat=42.98, lon=47.50, handling_norm_hours=12),
        Port(id="port_aktau", name="Актау (демо)", country="KZ", timezone="Asia/Aqtau", lat=43.65, lon=51.17, handling_norm_hours=12),
        Port(id="port_baku", name="Баку (демо)", country="AZ", timezone="Asia/Baku", lat=40.38, lon=49.87, handling_norm_hours=10),
        Port(id="port_anzali", name="Энзели (демо)", country="IR", timezone="Asia/Tehran", lat=37.47, lon=49.46, handling_norm_hours=10),
    ]
    session.add_all(ports)

    services = [
        ScheduledService(
            id="svc_astr_anz_01",
            name="DEMO Astrakhan–Anzali 01",
            mode="sea",
            origin_port_id="port_astrakhan",
            destination_port_id="port_anzali",
            departure_at=msk(2026, 11, 14, 6),
            arrival_at=msk(2026, 11, 15, 18),
            cutoff_hours=6,
        ),
        ScheduledService(
            id="svc_astr_anz_02",
            name="DEMO Astrakhan–Anzali 02",
            mode="sea",
            origin_port_id="port_astrakhan",
            destination_port_id="port_anzali",
            departure_at=msk(2026, 11, 17, 12),
            arrival_at=msk(2026, 11, 18, 4),
            cutoff_hours=6,
        ),
        ScheduledService(
            id="svc_makh_anz_01",
            name="DEMO Makhachkala–Anzali 01",
            mode="sea",
            origin_port_id="port_makhachkala",
            destination_port_id="port_anzali",
            departure_at=msk(2026, 11, 15, 20),
            arrival_at=msk(2026, 11, 16, 18),
            cutoff_hours=6,
        ),
        ScheduledService(
            id="svc_aktau_anz_01",
            name="DEMO Aktau–Anzali 01",
            mode="sea",
            origin_port_id="port_aktau",
            destination_port_id="port_anzali",
            departure_at=msk(2026, 11, 15, 16),
            arrival_at=msk(2026, 11, 16, 14),
            cutoff_hours=6,
            capacity_teu=0,
        ),
    ]
    session.add_all(services)

    # --- SCT-2048 main scenario ---
    s2048 = Shipment(
        id="shp_sct_2048",
        reference="SCT-2048",
        cargo_description="Промышленное оборудование",
        cargo_tonnes=22.4,
        container_no="MSCU 481209-6",
        equipment="1 × 40′ HC",
        route_from="Астрахань",
        route_to="Энзели",
        current_stage="Ожидание погрузки",
        current_location="порт Астрахань, терминал № 2",
        attention_title="△ SCT-2048 · +18 часов",
        attention_detail="Астрахань → Энзели\nПогодные ограничения и очередь",
        risk_headline="△ Риск пропустить морской рейс",
        risk_detail="Ожидаемая задержка — 18 часов. Ветер до 18 м/с ограничивает погрузку; очередь в порту — 10 часов.",
        cost_rub=180000,
        co2e_tonnes=1.84,
        status="in_transit",
        risk_level="high",
        planned_eta=msk(2026, 11, 18, 14),
        predicted_eta=msk(2026, 11, 19, 8),
        delay_hours=18.0,
        missed_connection=True,
        active_scenario="storm",
        created_at=now - timedelta(days=2),
    )
    session.add(s2048)

    legs_2048 = [
        TransportLeg(
            id="leg_2048_1",
            shipment_id=s2048.id,
            sequence=1,
            mode="rail",
            label="Железная дорога",
            origin_name="Астрахань-сорт.",
            destination_name="Астрахань порт",
            destination_port_id="port_astrakhan",
            distance_km=28,
            planned_departure=msk(2026, 11, 12, 4),
            planned_arrival=msk(2026, 11, 12, 8),
            actual_departure=msk(2026, 11, 12, 3, 40),
            actual_arrival=msk(2026, 11, 12, 7, 40),
            predicted_departure=msk(2026, 11, 12, 3, 40),
            predicted_arrival=msk(2026, 11, 12, 7, 40),
            status="completed",
            stage_status_label="✓ Завершён",
        ),
        TransportLeg(
            id="leg_2048_2",
            shipment_id=s2048.id,
            sequence=2,
            mode="port_handling",
            label="Порт",
            origin_name="Астрахань — приём",
            destination_name="Астрахань — погрузка",
            origin_port_id="port_astrakhan",
            destination_port_id="port_astrakhan",
            distance_km=5,
            planned_departure=msk(2026, 11, 12, 8),
            planned_arrival=msk(2026, 11, 13, 18),
            predicted_departure=msk(2026, 11, 12, 8),
            predicted_arrival=msk(2026, 11, 14, 12),
            status="in_progress",
            stage_status_label="◉ Погрузка",
        ),
        TransportLeg(
            id="leg_2048_3",
            shipment_id=s2048.id,
            sequence=3,
            mode="sea",
            label="Море",
            origin_name="Астрахань",
            destination_name="Энзели",
            origin_port_id="port_astrakhan",
            destination_port_id="port_anzali",
            distance_km=780,
            planned_departure=msk(2026, 11, 14, 6),
            planned_arrival=msk(2026, 11, 15, 18),
            predicted_departure=msk(2026, 11, 17, 12),
            predicted_arrival=msk(2026, 11, 18, 4),
            scheduled_service_id="svc_astr_anz_02",
            planned_scheduled_service_id="svc_astr_anz_01",
            status="rebooked",
            stage_status_label="○ Далее",
        ),
        TransportLeg(
            id="leg_2048_4",
            shipment_id=s2048.id,
            sequence=4,
            mode="port_handling",
            label="Порт",
            origin_name="Энзели — выгрузка",
            destination_name="Энзели — выдача",
            origin_port_id="port_anzali",
            destination_port_id="port_anzali",
            distance_km=4,
            planned_departure=msk(2026, 11, 17, 10),
            planned_arrival=msk(2026, 11, 17, 10),  # placeholder duration via predicted
            predicted_departure=msk(2026, 11, 18, 4),
            predicted_arrival=msk(2026, 11, 18, 14),
            status="planned",
            stage_status_label="○ Далее",
        ),
        TransportLeg(
            id="leg_2048_5",
            shipment_id=s2048.id,
            sequence=5,
            mode="road",
            label="Авто",
            origin_name="Энзели",
            destination_name="Склад получателя",
            origin_port_id="port_anzali",
            distance_km=320,
            planned_departure=msk(2026, 11, 17, 12),
            planned_arrival=msk(2026, 11, 18, 14),
            predicted_departure=msk(2026, 11, 18, 14),
            predicted_arrival=msk(2026, 11, 19, 8),
            status="planned",
            stage_status_label="○ Далее",
        ),
    ]
    # fix leg 4 planned arrival
    legs_2048[3].planned_arrival = msk(2026, 11, 17, 18)
    session.add_all(legs_2048)

    doc_specs_2048 = [
        ("commercial_invoice", "complete", msk(2026, 11, 12, 9, 12), "инвойс проверен"),
        ("packing_list", "submitted", msk(2026, 11, 12, 9, 35), "упаковочный лист добавлен"),
        ("bill_of_lading_draft", "accepted_for_review", msk(2026, 11, 12, 9, 48), "пакет v2 · накладная на проверке"),
        ("certificate_of_origin", "incomplete", msk(2026, 11, 12, 10, 10), "не указан код ТН ВЭД"),
        ("insurance_policy", "missing", None, "файл не добавлен"),
    ]
    for dtype, status, updated, note in doc_specs_2048:
        doc = Document(
            id=_uid("doc"),
            shipment_id=s2048.id,
            document_type=dtype,
            status=status,
            required=True,
            payload={},
            updated_at=updated or now,
        )
        session.add(doc)
        session.add(
            DocumentStatusHistory(
                id=_uid("dsh"),
                document_id=doc.id,
                status=status,
                note=note,
                changed_at=updated or now,
                actor="seed",
            )
        )

    for hh, mm, title, etype in [
        (10, 42, "Прогноз обновлён: +18 ч к плану", "forecast_updated"),
        (9, 20, "Порт сообщил об ограничении погрузки", "port_restriction"),
        (7, 40, "Контейнер принят на терминале", "terminal_received"),
    ]:
        session.add(
            Event(
                id=_uid("evt"),
                shipment_id=s2048.id,
                event_type=etype,
                title=title,
                occurred_at=msk(2026, 11, 12, hh, mm),
                available_at=msk(2026, 11, 12, hh, mm),
                payload={},
                source="seed",
            )
        )

    session.add(
        WeatherForecast(
            id=_uid("wx"),
            port_id="port_astrakhan",
            forecast_for=msk(2026, 11, 13, 12),
            available_at=now,
            severity_index=0.85,
            wind_ms=18.0,
        )
    )

    # --- SCT-2051 ---
    s2051 = Shipment(
        id="shp_sct_2051",
        reference="SCT-2051",
        cargo_description="Текстиль",
        cargo_tonnes=18.0,
        container_no="TEMU 220145-1",
        equipment="1 × 40′ HC",
        route_from="Актау",
        route_to="Баку",
        current_stage="Железная дорога",
        current_location="участок Актау",
        attention_title="SCT-2051 · пакет неполный",
        attention_detail="Не указан код ТН ВЭД",
        cost_rub=120000,
        co2e_tonnes=0.92,
        status="in_transit",
        risk_level="medium",
        planned_eta=msk(2026, 11, 17, 12, 30),
        predicted_eta=msk(2026, 11, 17, 12, 30),
        delay_hours=0.0,
        active_scenario="normal",
        created_at=now - timedelta(days=1),
    )
    session.add(s2051)
    session.add(
        TransportLeg(
            id="leg_2051_1",
            shipment_id=s2051.id,
            sequence=1,
            mode="rail",
            label="Железная дорога",
            origin_name="Актау",
            destination_name="Баку",
            distance_km=480,
            planned_departure=msk(2026, 11, 15, 8),
            planned_arrival=msk(2026, 11, 17, 12, 30),
            predicted_departure=msk(2026, 11, 15, 8),
            predicted_arrival=msk(2026, 11, 17, 12, 30),
            status="in_progress",
            stage_status_label="◉ В пути",
        )
    )
    for dtype, status, required in [
        ("commercial_invoice", "complete", True),
        ("packing_list", "complete", True),
        ("bill_of_lading_draft", "submitted", True),
        ("certificate_of_origin", "incomplete", True),
        ("insurance_policy", "missing", True),
    ]:
        doc = Document(
            id=_uid("doc"),
            shipment_id=s2051.id,
            document_type=dtype,
            status=status,
            required=required,
            payload={},
            updated_at=now,
        )
        session.add(doc)

    # --- SCT-2039 ---
    s2039 = Shipment(
        id="shp_sct_2039",
        reference="SCT-2039",
        cargo_description="Металлопрокат",
        cargo_tonnes=26.0,
        container_no="MSKU 991122-3",
        equipment="1 × 40′ HC",
        route_from="Баку",
        route_to="Актау",
        current_stage="Разгрузка в порту",
        current_location="порт Актау",
        attention_title="SCT-2039 · задержан на 6 ч",
        attention_detail="Ожидание разгрузки в Актау",
        cost_rub=95000,
        co2e_tonnes=1.1,
        status="at_risk",
        risk_level="medium",
        planned_eta=msk(2026, 11, 15, 10),
        predicted_eta=msk(2026, 11, 15, 16),
        delay_hours=6.0,
        active_scenario="port_congestion",
        created_at=now - timedelta(days=3),
    )
    session.add(s2039)
    session.add(
        TransportLeg(
            id="leg_2039_1",
            shipment_id=s2039.id,
            sequence=1,
            mode="port_handling",
            label="Порт",
            origin_name="Актау — разгрузка",
            destination_name="Актау — выдача",
            origin_port_id="port_aktau",
            destination_port_id="port_aktau",
            distance_km=3,
            planned_departure=msk(2026, 11, 15, 8),
            planned_arrival=msk(2026, 11, 15, 10),
            predicted_departure=msk(2026, 11, 15, 12),
            predicted_arrival=msk(2026, 11, 15, 16),
            status="in_progress",
            stage_status_label="◉ Разгрузка",
        )
    )
    for dtype in [
        "commercial_invoice",
        "packing_list",
        "bill_of_lading_draft",
        "certificate_of_origin",
        "insurance_policy",
    ]:
        session.add(
            Document(
                id=_uid("doc"),
                shipment_id=s2039.id,
                document_type=dtype,
                status="complete",
                required=True,
                payload={},
                updated_at=now,
            )
        )

    await session.commit()
    from app.services.tracking import ensure_tracking_data

    await ensure_tracking_data(session)
    evaluate_models()


def _write_history_csv() -> None:
    path = DATA / "synthetic_leg_history.csv"
    rows = []
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    modes = ["rail", "port_handling", "sea", "road"]
    for i in range(120):
        as_of = base + timedelta(days=i * 2)
        mode = modes[i % 4]
        weather = (i % 10) / 10.0
        queue = float(i % 15)
        doc = float(i % 8)
        delay = 1.5 + weather * 9 + max(0, queue - 4) * 0.7 + doc * 0.4 + (i % 3) * 0.2
        rows.append(
            {
                "as_of": as_of.isoformat(),
                "actual_end": (as_of + timedelta(hours=20 + delay)).isoformat(),
                "mode": mode,
                "weather_severity": weather,
                "port_queue_hours": queue,
                "doc_delay_hours": doc,
                "delay_hours": round(delay, 2),
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)


SCENARIOS = {
    "normal": {
        "label": "Обычные условия",
        "weather_severity_index": 0.15,
        "port_queue_hours": 4.0,
        "document_delay_hours": 0.0,
    },
    "storm": {
        "label": "Шторм",
        "weather_severity_index": 0.85,
        "port_queue_hours": 10.0,
        "document_delay_hours": 0.0,
    },
    "port_congestion": {
        "label": "Перегрузка порта",
        "weather_severity_index": 0.35,
        "port_queue_hours": 18.0,
        "document_delay_hours": 2.0,
    },
}
