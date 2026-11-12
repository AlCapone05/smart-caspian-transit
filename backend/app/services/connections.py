"""Connection / sailing recalculation with demo schedules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ScheduledService, Shipment, TransportLeg
from app.services.prediction import DelayEstimate, estimate_extra_delay


@dataclass
class RecalcResult:
    shipment: Shipment
    missed_connection: bool
    missed_service_id: Optional[str]
    next_service_id: Optional[str]
    delay_estimate: DelayEstimate
    risk_level: str


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def recalculate_shipment(
    session: AsyncSession,
    shipment_id: str,
    *,
    weather_severity: float,
    port_queue_hours: float,
    document_delay_hours: float,
    as_of: Optional[datetime] = None,
) -> RecalcResult:
    as_of = _aware(as_of or datetime.now(timezone.utc))

    result = await session.execute(
        select(Shipment)
        .where(Shipment.id == shipment_id)
        .options(selectinload(Shipment.legs), selectinload(Shipment.documents))
    )
    shipment = result.scalar_one()
    legs = sorted(shipment.legs, key=lambda x: x.sequence)

    delay_est = estimate_extra_delay(
        mode="port_handling",
        weather_severity=weather_severity,
        port_queue_hours=port_queue_hours,
        document_delay_hours=document_delay_hours,
    )

    # Find port handling at Russian port (sequence 2) and sea leg (sequence 3)
    handling = next((l for l in legs if l.mode == "port_handling" and l.sequence == 2), None)
    sea = next((l for l in legs if l.mode == "sea"), None)
    road = next((l for l in legs if l.mode == "road"), None)
    rail = next((l for l in legs if l.mode == "rail"), None)
    ir_handling = next((l for l in legs if l.mode == "port_handling" and l.sequence == 4), None)

    missed = False
    missed_service_id: Optional[str] = None
    next_service_id: Optional[str] = None

    # Rail assumed on plan / slight weather impact on first mile
    if rail:
        rail_extra = round(weather_severity * 2.0, 1)
        rail.predicted_departure = _aware(rail.planned_departure)
        rail.predicted_arrival = _aware(rail.planned_arrival) + timedelta(hours=rail_extra)
        rail.status = "predicted"

    ready_at = _aware(handling.planned_departure) if handling else as_of
    if rail and rail.predicted_arrival:
        ready_at = rail.predicted_arrival

    # Port handling duration = norm + queue + weather/doc extras (tuned so storm misses sailing)
    handling_hours = 12.0 + port_queue_hours * 1.2 + weather_severity * 18.0 + document_delay_hours * 0.3
    if handling:
        handling.predicted_departure = ready_at
        handling.predicted_arrival = ready_at + timedelta(hours=handling_hours)
        handling.status = "at_risk" if port_queue_hours >= 12 or weather_severity >= 0.6 else "predicted"
        cargo_ready_for_sea = handling.predicted_arrival
    else:
        cargo_ready_for_sea = ready_at + timedelta(hours=handling_hours)

    if sea:
        services = (
            await session.execute(
                select(ScheduledService)
                .where(
                    ScheduledService.origin_port_id == sea.origin_port_id,
                    ScheduledService.destination_port_id == sea.destination_port_id,
                    ScheduledService.mode == "sea",
                )
                .order_by(ScheduledService.departure_at)
            )
        ).scalars().all()

        planned_id = sea.planned_scheduled_service_id or sea.scheduled_service_id
        planned = next((s for s in services if s.id == planned_id), None)
        if planned is None and services:
            planned = services[0]
            planned_id = planned.id
            if not sea.planned_scheduled_service_id:
                sea.planned_scheduled_service_id = planned_id

        chosen: Optional[ScheduledService] = None
        for svc in services:
            cutoff = _aware(svc.departure_at) - timedelta(hours=svc.cutoff_hours)
            if cargo_ready_for_sea <= cutoff and svc.compatible_cargo == "container":
                chosen = svc
                break

        if planned and chosen and chosen.id != planned.id:
            missed = True
            missed_service_id = planned.id
            next_service_id = chosen.id
        elif planned and chosen is None:
            missed = True
            missed_service_id = planned.id
            next_service_id = None
        elif chosen:
            next_service_id = chosen.id
            if planned and cargo_ready_for_sea > (
                _aware(planned.departure_at) - timedelta(hours=planned.cutoff_hours)
            ):
                missed = True
                missed_service_id = planned.id

        if chosen:
            sea.scheduled_service_id = chosen.id
            sea.predicted_departure = _aware(chosen.departure_at)
            sea.predicted_arrival = _aware(chosen.arrival_at)
            sea.status = "rebooked" if missed else "predicted"
        else:
            # No feasible sailing — push far and mark
            sea.predicted_departure = cargo_ready_for_sea + timedelta(hours=48)
            sea.predicted_arrival = sea.predicted_departure + timedelta(hours=36)
            sea.status = "no_sailing"
            missed = True
            if planned:
                missed_service_id = planned.id

    # Iranian handling + road cascade
    anchor = sea.predicted_arrival if sea and sea.predicted_arrival else cargo_ready_for_sea
    if ir_handling:
        ir_h = 10.0 + (2.0 if weather_severity > 0.5 else 0.0)
        ir_handling.predicted_departure = _aware(anchor)
        ir_handling.predicted_arrival = _aware(anchor) + timedelta(hours=ir_h)
        ir_handling.status = "predicted"
        road_start = ir_handling.predicted_arrival
    else:
        road_start = _aware(anchor)

    if road:
        road_hours = (road.planned_arrival - road.planned_departure).total_seconds() / 3600.0
        road.predicted_departure = road_start
        road.predicted_arrival = road_start + timedelta(hours=road_hours)
        road.status = "predicted"

    if sea or road or handling:
        predicted_eta = road.predicted_arrival if road and road.predicted_arrival else _aware(shipment.planned_eta)
        if not road and ir_handling and ir_handling.predicted_arrival:
            predicted_eta = ir_handling.predicted_arrival
        elif not road and sea and sea.predicted_arrival:
            predicted_eta = sea.predicted_arrival
        elif not road and handling and handling.predicted_arrival and not sea:
            predicted_eta = handling.predicted_arrival
    else:
        # Rail-only / simple routes: push last leg by scenario extras
        extra = delay_est.extra_hours if hasattr(delay_est, "extra_hours") else (
            weather_severity * 10 + max(0.0, port_queue_hours - 4) * 0.5 + document_delay_hours
        )
        last = legs[-1] if legs else None
        if last:
            base_arr = _aware(last.actual_arrival or last.predicted_arrival or last.planned_arrival)
            last.predicted_arrival = base_arr + timedelta(hours=extra)
            last.status = "at_risk" if extra >= 6 else "predicted"
            if last.stage_status_label and "◉" not in (last.stage_status_label or ""):
                last.stage_status_label = "△ Задержка" if extra >= 6 else last.stage_status_label
            predicted_eta = last.predicted_arrival
        else:
            predicted_eta = _aware(shipment.planned_eta) + timedelta(hours=extra)

    delay_hours = max(0.0, (predicted_eta - _aware(shipment.planned_eta)).total_seconds() / 3600.0)

    factors = list(delay_est.factors)
    if missed:
        miss_h = 0.0
        if missed_service_id and next_service_id:
            # contribution approximated by sailing gap
            svc_rows = (await session.execute(select(ScheduledService))).scalars().all()
            svcs = {s.id: s for s in svc_rows}
            a, b = svcs.get(missed_service_id), svcs.get(next_service_id)
            if a and b:
                miss_h = round((_aware(b.departure_at) - _aware(a.departure_at)).total_seconds() / 3600.0, 1)
        factors.append(
            {
                "code": "missed_sailing",
                "label": "Пропущен морской рейс (правило стыковки)",
                "contribution_hours": miss_h,
                "note": "Следствие правила cutoff/расписания, не ML-причина.",
            }
        )

    if delay_hours >= 24 or missed:
        risk = "high"
    elif delay_hours >= 8:
        risk = "medium"
    else:
        risk = "low"

    # Incomplete docs bump risk
    required = [d for d in shipment.documents if d.required]
    if required:
        ok = sum(1 for d in required if d.status in {"accepted_for_review", "submitted", "complete"})
        if ok < len(required):
            if risk == "low":
                risk = "medium"
            factors.append(
                {
                    "code": "docs_incomplete",
                    "label": "Неполный комплект документов (тест)",
                    "contribution_hours": document_delay_hours,
                    "note": "Тестовый статус. Не является таможенным разрешением.",
                }
            )

    shipment.predicted_eta = predicted_eta
    shipment.delay_hours = round(delay_hours, 1)
    shipment.missed_connection = missed
    shipment.risk_level = risk
    if shipment.status not in {"delivered", "cancelled"}:
        shipment.status = "at_risk" if risk == "high" else "in_transit"

    delay_est.factors = factors
    await session.commit()
    await session.refresh(shipment)

    return RecalcResult(
        shipment=shipment,
        missed_connection=missed,
        missed_service_id=missed_service_id,
        next_service_id=next_service_id,
        delay_estimate=delay_est,
        risk_level=risk,
    )
