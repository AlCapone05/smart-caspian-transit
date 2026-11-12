import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_api_key
from app.config import get_settings
from app.db import get_db
from app.models import Event, Prediction, Shipment
from app.schemas.api import (
    AlternativesResponse,
    DocumentHistoryOut,
    DocumentsResponse,
    HealthOut,
    OverviewOut,
    PredeclareRequest,
    PredeclareResponse,
    SelectAlternativeRequest,
    ShipmentDetail,
    ShipmentsList,
    SimulateRequest,
    SimulateResponse,
)
from app.seed.bootstrap import SCENARIOS
from app.services.alternatives import build_alternatives
from app.services.connections import recalculate_shipment
from app.services.documents import document_history, documents_payload, predeclare
from app.services.serialize import leg_out, shipment_detail, shipment_summary

router = APIRouter()
settings = get_settings()
MSK = ZoneInfo("Europe/Moscow")


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(
        status="ok",
        data_quality=settings.data_quality,
        disclaimer="Smart Caspian Transit API · МОГГНИТ",
    )


@router.post("/assistant/chat", dependencies=[Depends(require_api_key)])
async def assistant_chat(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.assistant import chat as assistant_chat_service

    message = str((body or {}).get("message") or "")
    history = (body or {}).get("history")
    if history is not None and not isinstance(history, list):
        history = None
    result = await assistant_chat_service(db, message, history)
    result["data_quality"] = settings.data_quality
    return result


@router.get("/overview", response_model=OverviewOut, dependencies=[Depends(require_api_key)])
async def overview(db: AsyncSession = Depends(get_db)) -> OverviewOut:
    rows = (
        await db.execute(
            select(Shipment)
            .options(selectinload(Shipment.documents))
            .order_by(Shipment.reference)
        )
    ).scalars().all()
    items = [shipment_summary(s) for s in rows]
    active = sum(1 for s in rows if s.status not in {"delivered", "completed", "cancelled"})
    at_risk = sum(1 for s in rows if s.risk_level in {"high", "medium"})
    delayed = sum(1 for s in rows if s.delay_hours > 0)
    awaiting_docs = sum(
        1
        for s in rows
        if any(d.required and d.status in {"missing", "incomplete"} for d in s.documents)
    )
    kpis = {
        "active": active,
        "at_risk": at_risk,
        "delayed": delayed,
        "awaiting_docs": awaiting_docs,
    }
    attention = []
    for s in rows:
        if s.attention_title:
            attention.append(
                {
                    "shipment_id": s.id,
                    "reference": s.reference,
                    "title": s.attention_title,
                    "detail": s.attention_detail,
                    "risk_level": s.risk_level,
                    "delay_hours": s.delay_hours,
                }
            )
    attention.sort(key=lambda a: a["delay_hours"], reverse=True)
    now = datetime.now(timezone.utc)
    return OverviewOut(
        title="Обзор перевозок",
        subtitle=f"Каспийский коридор · {now.astimezone(MSK).day} ноября 2026",
        refreshed_at=now,
        kpis=kpis,
        attention=attention,
        shipments=items,
        selected_map_reference="SCT-2048",
        data_quality=settings.data_quality,
        disclaimer="Каспийский коридор · время МСК (UTC+3)",
    )


@router.get("/shipments", response_model=ShipmentsList, dependencies=[Depends(require_api_key)])
async def list_shipments(db: AsyncSession = Depends(get_db)) -> ShipmentsList:
    rows = (
        await db.execute(
            select(Shipment).options(selectinload(Shipment.documents)).order_by(Shipment.reference)
        )
    ).scalars().all()
    return ShipmentsList(items=[shipment_summary(s) for s in rows], data_quality=settings.data_quality)


@router.post("/shipments", dependencies=[Depends(require_api_key)])
async def create_shipment_route(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.shipments_crud import create_shipment

    try:
        return await create_shipment(db, body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/shipments/compare", dependencies=[Depends(require_api_key)])
async def shipments_compare(
    ids: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.services.workspace import compare_shipments

    id_list = [x.strip() for x in (ids or "").split(",") if x.strip()]
    return await compare_shipments(db, id_list)


@router.get("/shipments/{shipment_id}", response_model=ShipmentDetail, dependencies=[Depends(require_api_key)])
async def get_shipment(shipment_id: str, db: AsyncSession = Depends(get_db)) -> ShipmentDetail:
    result = await db.execute(
        select(Shipment)
        .where(Shipment.id == shipment_id)
        .options(
            selectinload(Shipment.legs),
            selectinload(Shipment.events),
            selectinload(Shipment.documents),
            selectinload(Shipment.predictions),
        )
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        # allow lookup by reference
        result = await db.execute(
            select(Shipment)
            .where(Shipment.reference == shipment_id)
            .options(
                selectinload(Shipment.legs),
                selectinload(Shipment.events),
                selectinload(Shipment.documents),
                selectinload(Shipment.predictions),
            )
        )
        shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(404, "Shipment not found")
    return ShipmentDetail(**shipment_detail(shipment))


@router.patch("/shipments/{shipment_id}", dependencies=[Depends(require_api_key)])
async def patch_shipment(shipment_id: str, body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.shipments_crud import update_shipment

    try:
        return await update_shipment(db, shipment_id, body)
    except ValueError as exc:
        raise HTTPException(404 if "not found" in str(exc).lower() else 400, str(exc)) from exc


@router.delete("/shipments/{shipment_id}", dependencies=[Depends(require_api_key)])
async def remove_shipment(shipment_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.shipments_crud import delete_shipment

    try:
        return await delete_shipment(db, shipment_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post(
    "/shipments/{shipment_id}/simulate",
    response_model=SimulateResponse,
    dependencies=[Depends(require_api_key)],
)
async def simulate(
    shipment_id: str,
    body: SimulateRequest,
    db: AsyncSession = Depends(get_db),
) -> SimulateResponse:
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    exists = result.scalar_one_or_none()
    if not exists:
        result = await db.execute(select(Shipment).where(Shipment.reference == shipment_id))
        exists = result.scalar_one_or_none()
        if not exists:
            raise HTTPException(404, "Shipment not found")
        shipment_id = exists.id

    from app.services.workspace import get_settings_payload

    scenario_key = (
        body.scenario
        or exists.active_scenario
        or get_settings_payload().get("default_scenario")
        or "storm"
    )
    if scenario_key in SCENARIOS:
        sc = SCENARIOS[scenario_key]
        weather = sc["weather_severity_index"]
        queue = sc["port_queue_hours"]
        doc_delay = sc["document_delay_hours"]
    else:
        weather = body.weather_severity_index
        queue = body.port_queue_hours
        doc_delay = body.document_delay_hours
        scenario_key = "custom"

    as_of = body.as_of or datetime.now(timezone.utc)
    recalc = await recalculate_shipment(
        db,
        shipment_id,
        weather_severity=weather,
        port_queue_hours=queue,
        document_delay_hours=doc_delay,
        as_of=as_of,
    )

    shipment = (
        await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    ).scalar_one()
    shipment.active_scenario = scenario_key
    if recalc.missed_connection:
        shipment.risk_headline = "△ Риск пропустить морской рейс"
        shipment.risk_detail = (
            f"Ожидаемая задержка — {shipment.delay_hours:.0f} часов. "
            f"Сценарий «{SCENARIOS.get(scenario_key, {}).get('label', scenario_key)}» (демо)."
        )
        shipment.attention_title = f"△ {shipment.reference} · +{shipment.delay_hours:.0f} часов"
        shipment.current_stage = "Ожидание погрузки"
    else:
        shipment.risk_headline = None
        shipment.risk_detail = None
        if shipment.delay_hours <= 0:
            shipment.attention_title = None

    for etype, payload in [
        ("simulator_weather", {"weather_severity_index": weather, "scenario": scenario_key}),
        ("simulator_port_queue", {"port_queue_hours": queue}),
        ("simulator_document_delay", {"document_delay_hours": doc_delay}),
    ]:
        db.add(
            Event(
                id=f"evt_{uuid.uuid4().hex[:10]}",
                shipment_id=shipment_id,
                event_type=etype,
                title=f"Симулятор: {etype}",
                occurred_at=as_of,
                available_at=as_of,
                payload=payload,
                source="simulator",
            )
        )

    pred = Prediction(
        id=f"prd_{uuid.uuid4().hex[:10]}",
        shipment_id=shipment_id,
        model_name=recalc.delay_estimate.model_name,
        as_of_ts=as_of,
        predicted_eta=shipment.predicted_eta,
        delay_hours=shipment.delay_hours,
        missed_connection=recalc.missed_connection,
        risk_factors=recalc.delay_estimate.factors,
        mae_hours_holdout=recalc.delay_estimate.mae_hours_holdout,
        notes="Точечный прогноз без интервала уверенности. Синтетические данные.",
        data_quality="synthetic_demo",
    )
    db.add(pred)
    await db.commit()

    result = await db.execute(
        select(Shipment).where(Shipment.id == shipment_id).options(selectinload(Shipment.legs))
    )
    shipment = result.scalar_one()

    return SimulateResponse(
        shipment_id=shipment_id,
        missed_connection=recalc.missed_connection,
        missed_service_id=recalc.missed_service_id,
        next_service_id=recalc.next_service_id,
        predicted_eta=shipment.predicted_eta,
        delay_hours=shipment.delay_hours,
        risk_level=shipment.risk_level,
        risk_factors=recalc.delay_estimate.factors,
        legs=[leg_out(l) for l in sorted(shipment.legs, key=lambda x: x.sequence)],
        model_name=recalc.delay_estimate.model_name,
        mae_hours_holdout=recalc.delay_estimate.mae_hours_holdout,
        active_scenario=scenario_key,
        data_quality="synthetic_demo",
    )


@router.get(
    "/shipments/{shipment_id}/alternatives",
    response_model=AlternativesResponse,
    dependencies=[Depends(require_api_key)],
)
async def alternatives(shipment_id: str, db: AsyncSession = Depends(get_db)) -> AlternativesResponse:
    shipment = await _resolve_shipment(db, shipment_id)
    data = await build_alternatives(db, shipment.id)
    return AlternativesResponse(**data)


@router.post(
    "/shipments/{shipment_id}/select-alternative",
    dependencies=[Depends(require_api_key)],
)
async def select_alternative(
    shipment_id: str,
    body: SelectAlternativeRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.services.alternatives import apply_alternative

    shipment = await _resolve_shipment(db, shipment_id)
    # reload legs for mutation
    shipment = await _resolve_shipment(db, shipment.id)
    result = await db.execute(
        select(Shipment)
        .where(Shipment.id == shipment.id)
        .options(selectinload(Shipment.legs), selectinload(Shipment.events))
    )
    shipment = result.scalar_one()
    alts = await build_alternatives(db, shipment.id)
    chosen = next((a for a in alts["alternatives"] if a["id"] == body.alternative_id), None)
    if not chosen:
        raise HTTPException(400, "Unknown alternative_id")
    if not chosen["feasible"]:
        raise HTTPException(400, chosen.get("infeasible_reason") or "Alternative not selectable")
    if chosen.get("is_current") and shipment.selected_alternative_id == body.alternative_id:
        raise HTTPException(400, "Alternative already selected")
    await apply_alternative(db, shipment, chosen)
    await db.commit()
    return {
        "shipment_id": shipment.id,
        "selected_alternative_id": body.alternative_id,
        "predicted_eta": shipment.predicted_eta,
        "delay_hours": shipment.delay_hours,
        "cost_rub": shipment.cost_rub,
        "co2e_tonnes": shipment.co2e_tonnes,
        "risk_headline": shipment.risk_headline,
        "data_quality": "synthetic_demo",
    }


@router.get(
    "/shipments/{shipment_id}/documents",
    response_model=DocumentsResponse,
    dependencies=[Depends(require_api_key)],
)
async def list_documents(shipment_id: str, db: AsyncSession = Depends(get_db)) -> DocumentsResponse:
    shipment = await _resolve_shipment(db, shipment_id, with_docs=True)
    return DocumentsResponse(**documents_payload(shipment))


@router.post(
    "/documents/predeclare",
    response_model=PredeclareResponse,
    dependencies=[Depends(require_api_key)],
)
async def documents_predeclare(body: PredeclareRequest, db: AsyncSession = Depends(get_db)) -> PredeclareResponse:
    shipment = await _resolve_shipment(db, body.shipment_id)
    doc = await predeclare(
        db,
        shipment_id=shipment.id,
        document_type=body.document_type,
        payload=body.payload,
    )
    return PredeclareResponse(
        document_id=doc.id,
        status=doc.status,
        disclaimer=doc.disclaimer,
        data_quality="synthetic_demo",
    )


@router.get(
    "/documents/{document_id}/history",
    response_model=DocumentHistoryOut,
    dependencies=[Depends(require_api_key)],
)
async def docs_history(document_id: str, db: AsyncSession = Depends(get_db)) -> DocumentHistoryOut:
    try:
        data = await document_history(db, document_id)
    except Exception as exc:
        raise HTTPException(404, "Document not found") from exc
    return DocumentHistoryOut(**data)


@router.get("/metrics/model", dependencies=[Depends(require_api_key)])
async def model_metrics() -> dict:
    from app.services.prediction import evaluate_models

    metrics = evaluate_models()
    return {
        "mae_hours": metrics,
        "split": "time-based 70/30 on synthetic_leg_history.csv",
        "note": "Метрики на синтетике; не переносить как качество продакшена.",
        "data_quality": "synthetic_demo",
    }


@router.get("/scenarios", dependencies=[Depends(require_api_key)])
async def scenarios() -> dict:
    return {"items": SCENARIOS, "data_quality": "synthetic_demo"}


@router.get("/documents/registry", dependencies=[Depends(require_api_key)])
async def documents_registry_view(db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.workspace import documents_registry

    return await documents_registry(db)


@router.get("/documents/workspace", dependencies=[Depends(require_api_key)])
async def documents_workspace_view(
    shipment_id: str = "shp_sct_2048",
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.services.workspace import documents_workspace

    try:
        return await documents_workspace(db, shipment_id)
    except Exception as exc:
        raise HTTPException(404, "Shipment not found") from exc


@router.post("/documents/add", dependencies=[Depends(require_api_key)])
async def documents_add(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.documents import add_or_update_document

    shipment_id = body.get("shipment_id")
    if not shipment_id:
        raise HTTPException(400, "shipment_id required")
    try:
        doc = await add_or_update_document(
            db,
            shipment_id=shipment_id,
            document_id=body.get("document_id"),
            document_type=body.get("document_type"),
            file_name=body.get("file_name")
            or (
                f"{body.get('document_type', 'document')}_demo.pdf"
                if body.get("mark_file_added")
                else None
            ),
            hs_code=body.get("hs_code"),
            mark_complete=bool(body.get("mark_complete")),
            payload=body.get("payload") or {"demo": True},
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "document_id": doc.id,
        "document_type": doc.document_type,
        "status": doc.status,
        "disclaimer": doc.disclaimer,
        "data_quality": "synthetic_demo",
    }


@router.post("/documents/{document_id}/fix", dependencies=[Depends(require_api_key)])
async def documents_fix(
    document_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.services.workspace import fix_document_field

    try:
        doc = await fix_document_field(
            db,
            document_id,
            hs_code=body.get("hs_code"),
            mark_file_added=bool(body.get("mark_file_added")),
            file_name=body.get("file_name"),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(404, "Document not found") from exc
    return {
        "document_id": doc.id,
        "status": doc.status,
        "disclaimer": doc.disclaimer,
        "data_quality": "synthetic_demo",
    }


@router.post("/documents/precheck", dependencies=[Depends(require_api_key)])
async def documents_precheck(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.workspace import submit_precheck

    shipment_id = body.get("shipment_id") or "shp_sct_2048"
    return await submit_precheck(db, shipment_id)


@router.get("/analytics", dependencies=[Depends(require_api_key)])
async def analytics(db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.workspace import analytics_dashboard

    return await analytics_dashboard(db)


@router.get("/tracking", dependencies=[Depends(require_api_key)])
async def tracking_get(db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.tracking import tracking_dashboard

    return await tracking_dashboard(db)


@router.post("/tracking/tick", dependencies=[Depends(require_api_key)])
async def tracking_tick(db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.tracking import tick_tracking

    return await tick_tracking(db, hours=0.9)


@router.post("/tracking/vessels/{vessel_id}/select-route", dependencies=[Depends(require_api_key)])
async def tracking_select_route(vessel_id: str, body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.tracking import select_vessel_route

    alt = (body or {}).get("alternative_id")
    if not alt:
        raise HTTPException(400, "alternative_id required")
    try:
        return await select_vessel_route(db, vessel_id, str(alt))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/tracking/alerts", dependencies=[Depends(require_api_key)])
async def tracking_alerts(db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.tracking import tracking_dashboard

    data = await tracking_dashboard(db)
    return {
        "items": data["alerts"],
        "disclaimer": data["disclaimer"],
        "data_quality": "synthetic_demo",
    }


@router.get("/notifications", dependencies=[Depends(require_api_key)])
async def notifications(db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.workspace import get_settings_payload

    cfg = get_settings_payload()
    rows = (
        await db.execute(
            select(Shipment)
            .options(selectinload(Shipment.documents))
            .order_by(Shipment.reference)
        )
    ).scalars().all()
    items: list[dict] = []
    now = datetime.now(timezone.utc)
    for s in rows:
        if s.attention_title:
            items.append(
                {
                    "id": f"attn_{s.id}",
                    "shipment_id": s.id,
                    "reference": s.reference,
                    "title": s.attention_title,
                    "detail": s.attention_detail or s.risk_detail or s.route_from,
                    "kind": "risk" if s.risk_level in {"high", "medium"} else "info",
                    "created_label": now.astimezone(MSK).strftime("%H:%M"),
                }
            )
        docs_bad = [d for d in s.documents if d.required and d.status in {"missing", "incomplete"}]
        if docs_bad:
            items.append(
                {
                    "id": f"docs_{s.id}",
                    "shipment_id": s.id,
                    "reference": s.reference,
                    "title": f"{s.reference} · документы",
                    "detail": f"Требуют внимания: {len(docs_bad)} документ(ов)",
                    "kind": "docs",
                    "created_label": now.astimezone(MSK).strftime("%H:%M"),
                }
            )
    try:
        from app.services.tracking import tracking_dashboard

        track = await tracking_dashboard(db)
        vessel_by_id = {v["id"]: v for v in track.get("vessels", [])}
        for a in track.get("alerts", [])[:6]:
            ship_id = "shp_sct_2048"
            for vid in a.get("affected_vessel_ids") or []:
                linked = vessel_by_id.get(vid, {}).get("shipment_id")
                if linked:
                    ship_id = linked
                    break
            items.append(
                {
                    "id": a["id"],
                    "shipment_id": ship_id,
                    "reference": a.get("port_id") or "WX",
                    "title": a["title"],
                    "detail": a["detail"],
                    "kind": "weather",
                    "created_label": now.astimezone(MSK).strftime("%H:%M"),
                }
            )
    except Exception:
        pass
    if not cfg.get("notifications_enabled"):
        return {
            "items": [],
            "unread": 0,
            "enabled": False,
            "disclaimer": "Уведомления выключены в настройках.",
            "data_quality": "synthetic_demo",
        }
    return {
        "items": items[:12],
        "unread": len(items),
        "enabled": True,
        "disclaimer": "События по рискам стыковки, погоде и документам.",
        "data_quality": "operational",
    }


@router.get("/settings", dependencies=[Depends(require_api_key)])
async def settings_get() -> dict:
    from app.services.workspace import get_settings_payload

    return get_settings_payload()


@router.patch("/settings", dependencies=[Depends(require_api_key)])
async def settings_patch(body: dict) -> dict:
    from app.services.workspace import update_settings_payload

    return update_settings_payload(body)


async def _resolve_shipment(
    db: AsyncSession, shipment_id: str, *, with_docs: bool = False
) -> Shipment:
    opts = []
    if with_docs:
        opts.append(selectinload(Shipment.documents))
    q = select(Shipment).where(Shipment.id == shipment_id)
    if opts:
        q = q.options(*opts)
    shipment = (await db.execute(q)).scalar_one_or_none()
    if shipment:
        return shipment
    q2 = select(Shipment).where(Shipment.reference == shipment_id)
    if opts:
        q2 = q2.options(*opts)
    shipment = (await db.execute(q2)).scalar_one_or_none()
    if not shipment:
        raise HTTPException(404, "Shipment not found")
    return shipment
