from app.models import Shipment
from app.services.co2 import estimate_route_co2e_kg
from app.services.documents import documents_payload


def leg_out(leg) -> dict:
    return {
        "id": leg.id,
        "sequence": leg.sequence,
        "mode": leg.mode,
        "label": leg.label or leg.mode,
        "origin_name": leg.origin_name,
        "destination_name": leg.destination_name,
        "distance_km": leg.distance_km,
        "planned_departure": leg.planned_departure,
        "planned_arrival": leg.planned_arrival,
        "predicted_departure": leg.predicted_departure,
        "predicted_arrival": leg.predicted_arrival,
        "actual_departure": leg.actual_departure,
        "actual_arrival": leg.actual_arrival,
        "scheduled_service_id": leg.scheduled_service_id,
        "status": leg.status,
        "stage_status_label": leg.stage_status_label,
        "data_quality": leg.data_quality,
    }


def docs_progress(s: Shipment) -> dict:
    required = [d for d in s.documents if d.required]
    total = len(required) or 5
    # в пакете = всё, кроме полного отсутствия файла (как вкладка Документы)
    ready = sum(1 for d in required if d.status != "missing")
    has_issues = any(d.status in {"missing", "incomplete"} for d in required)
    return {
        "ready": ready,
        "total": total,
        "label": f"{'△ ' if has_issues else '✓ '}{ready} из {total}",
    }


def shipment_summary(s: Shipment) -> dict:
    docs = docs_progress(s)
    return {
        "id": s.id,
        "reference": s.reference,
        "status": s.status,
        "risk_level": s.risk_level,
        "route_from": s.route_from,
        "route_to": s.route_to,
        "route_label": f"{s.route_from} → {s.route_to}",
        "current_stage": s.current_stage,
        "planned_eta": s.planned_eta,
        "predicted_eta": s.predicted_eta,
        "delay_hours": s.delay_hours,
        "missed_connection": s.missed_connection,
        "cargo_description": s.cargo_description,
        "container_no": s.container_no or "",
        "documents_ready": docs["ready"],
        "documents_total": docs["total"],
        "documents_label": docs["label"],
        "attention_title": s.attention_title,
        "attention_detail": s.attention_detail,
        "data_quality": s.data_quality,
    }


def _normalize_risk_factors(raw) -> list[dict]:
    """Ensure prediction risk_factors match RiskFactor schema (dict, not bare strings)."""
    out: list[dict] = []
    if not raw:
        return out
    for item in raw:
        if isinstance(item, dict) and item.get("code"):
            out.append(
                {
                    "code": str(item.get("code")),
                    "label": str(item.get("label") or item.get("code")),
                    "contribution_hours": float(item.get("contribution_hours") or 0),
                    "note": str(
                        item.get("note")
                        or "Ассоциативный фактор, не доказанная причина задержки."
                    ),
                }
            )
        elif isinstance(item, str) and item.strip():
            out.append(
                {
                    "code": item.strip(),
                    "label": item.strip().replace("_", " "),
                    "contribution_hours": 0.0,
                    "note": "Ассоциативный фактор, не доказанная причина задержки.",
                }
            )
    return out


def shipment_detail(s: Shipment) -> dict:
    preds = sorted(s.predictions, key=lambda p: p.as_of_ts, reverse=True)
    latest = None
    if preds:
        p = preds[0]
        latest = {
            "id": p.id,
            "model_name": p.model_name,
            "as_of_ts": p.as_of_ts,
            "predicted_eta": p.predicted_eta,
            "delay_hours": p.delay_hours,
            "missed_connection": p.missed_connection,
            "risk_factors": _normalize_risk_factors(p.risk_factors),
            "mae_hours_holdout": p.mae_hours_holdout,
            "notes": p.notes,
            "data_quality": p.data_quality,
        }
    timeline = sorted(s.events, key=lambda e: e.occurred_at, reverse=True)
    docs = documents_payload(s)
    progress = docs_progress(s)
    legs_meta = [{"mode": l.mode, "distance_km": l.distance_km} for l in s.legs]
    co2 = s.co2e_tonnes or round(estimate_route_co2e_kg(legs_meta, s.cargo_tonnes) / 1000.0, 2)
    return {
        "id": s.id,
        "reference": s.reference,
        "cargo_description": s.cargo_description,
        "cargo_tonnes": s.cargo_tonnes,
        "container_no": s.container_no,
        "equipment": s.equipment,
        "cargo_line": f"{s.container_no} · {s.equipment} · {s.cargo_tonnes} т · {s.cargo_description}",
        "route_from": s.route_from,
        "route_to": s.route_to,
        "route_label": f"{s.route_from} → {s.route_to}",
        "current_stage": s.current_stage,
        "current_location": s.current_location,
        "status": s.status,
        "risk_level": s.risk_level,
        "risk_headline": s.risk_headline,
        "risk_detail": s.risk_detail,
        "planned_eta": s.planned_eta,
        "predicted_eta": s.predicted_eta,
        "delay_hours": s.delay_hours,
        "missed_connection": s.missed_connection,
        "selected_alternative_id": s.selected_alternative_id,
        "active_scenario": s.active_scenario,
        "cost_rub": s.cost_rub,
        "co2e_tonnes": co2,
        "documents_ready": progress["ready"],
        "documents_total": progress["total"],
        "legs": [leg_out(l) for l in sorted(s.legs, key=lambda x: x.sequence)],
        "timeline": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "title": e.title or e.event_type,
                "occurred_at": e.occurred_at,
                "available_at": e.available_at,
                "payload": e.payload,
                "source": e.source,
                "data_quality": e.data_quality,
            }
            for e in timeline
        ],
        "documents": docs,
        "latest_prediction": latest,
        "schedule_disclaimer": (
            "Маршруты и ETA · время МСК (UTC+3)"
        ),
        "data_quality": s.data_quality,
    }
