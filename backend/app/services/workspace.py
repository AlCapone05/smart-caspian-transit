"""Workspace payloads for Documents / Analytics / Settings / Compare."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Document, DocumentStatusHistory, Shipment
from app.services.documents import DOC_TITLES, PACKAGE_TYPES, add_or_update_document, ensure_package_docs
from app.services.prediction import evaluate_models
from app.services.serialize import shipment_summary

MSK = ZoneInfo("Europe/Moscow")
SETTINGS_PATH = Path(__file__).resolve().parents[2] / "data" / "app_settings.json"

STATUS_UI = {
    "complete": {"code": "verified", "label": "✓ Проверен", "tone": "success"},
    "submitted": {"code": "added", "label": "○ Добавлен", "tone": "neutral"},
    "accepted_for_review": {"code": "review", "label": "◷ На проверке", "tone": "progress"},
    "incomplete": {"code": "warning", "label": "△ Не хватает данных", "tone": "warning"},
    "missing": {"code": "missing", "label": "○ Файл не добавлен", "tone": "neutral"},
}

_DEFAULT_SETTINGS = {
    "display_timezone": "Europe/Moscow",
    "locale": "ru-RU",
    "notifications_enabled": True,
    "demo_mode": False,
    "api_key_hint": "demo-key",
    "default_scenario": "storm",
    "co2_uncertainty_pct": 20,
    "operator_name": "Адам Табиев",
    "operator_role": "Логист · Каспий",
}


def _msk_label(dt: datetime | None) -> str:
    if not dt:
        return "—"
    local = dt.astimezone(MSK) if dt.tzinfo else dt.replace(tzinfo=timezone.utc).astimezone(MSK)
    months = {
        1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
        7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек",
    }
    return f"{local.day} {months[local.month]}, {local.strftime('%H:%M')}"


def _action_for(status: str) -> str:
    return {
        "complete": "Открыть",
        "submitted": "Открыть",
        "accepted_for_review": "История",
        "incomplete": "Исправить",
        "missing": "Добавить файл",
    }.get(status, "Открыть")


def _build_fixes(docs: list[Document]) -> list[dict]:
    fixes: list[dict] = []
    for d in docs:
        title = DOC_TITLES.get(d.document_type, d.document_type)
        if d.status == "incomplete":
            fixes.append(
                {
                    "document_id": d.id,
                    "document_type": d.document_type,
                    "title": f"{title} · поле «Код ТН ВЭД»",
                    "field": "hs_code",
                    "placeholder": "Укажите 10-значный код",
                    "error": "Код отсутствует. Заполните поле и сохраните документ.",
                }
            )
        elif d.status == "missing":
            if d.document_type in {"certificate_of_origin", "hs_code_declaration"}:
                fixes.append(
                    {
                        "document_id": d.id,
                        "document_type": d.document_type,
                        "title": f"{title} · укажите ТН ВЭД",
                        "field": "hs_code",
                        "placeholder": "Укажите 10-значный код",
                        "error": "Документ отсутствует. Добавьте код ТН ВЭД или файл.",
                    }
                )
            fixes.append(
                {
                    "document_id": d.id,
                    "document_type": d.document_type,
                    "title": f"{title} · добавьте PDF, до 10 МБ.",
                    "field": "file",
                    "placeholder": None,
                    "error": None,
                }
            )
    return fixes


async def documents_registry(session: AsyncSession) -> dict:
    rows = (
        await session.execute(
            select(Shipment)
            .options(selectinload(Shipment.documents))
            .order_by(Shipment.reference)
        )
    ).scalars().all()
    items = []
    for s in rows:
        await ensure_package_docs(session, s)
        required = [d for d in s.documents if d.required]
        ready = sum(1 for d in required if d.status != "missing")
        issues = sum(1 for d in required if d.status in {"missing", "incomplete"})
        items.append(
            {
                "shipment_id": s.id,
                "reference": s.reference,
                "route_label": f"{s.route_from} → {s.route_to}",
                "completeness_label": f"{ready} из {len(required) or 5}",
                "issues": issues,
                "attention": issues > 0,
            }
        )
    await session.commit()
    return {
        "items": items,
        "default_shipment_id": next(
            (i["shipment_id"] for i in items if i["attention"]),
            items[0]["shipment_id"] if items else "shp_sct_2048",
        ),
        "data_quality": "synthetic_demo",
        "disclaimer": "Реестр комплекта документов перевозки.",
    }


async def documents_workspace(session: AsyncSession, shipment_id: str) -> dict:
    result = await session.execute(
        select(Shipment)
        .where((Shipment.id == shipment_id) | (Shipment.reference == shipment_id))
        .options(selectinload(Shipment.documents).selectinload(Document.history))
    )
    shipment = result.scalar_one()
    await ensure_package_docs(session, shipment)
    await session.commit()
    result = await session.execute(
        select(Shipment)
        .where(Shipment.id == shipment.id)
        .options(selectinload(Shipment.documents).selectinload(Document.history))
    )
    shipment = result.scalar_one()

    # Hide optional legacy HS declaration from the package table
    docs = sorted(
        [d for d in shipment.documents if d.required or d.document_type in PACKAGE_TYPES],
        key=lambda d: PACKAGE_TYPES.index(d.document_type) if d.document_type in PACKAGE_TYPES else 99,
    )
    docs = [d for d in docs if d.document_type != "hs_code_declaration"]
    required = [d for d in docs if d.required]
    ready = sum(1 for d in required if d.status != "missing")
    issues_fields = sum(1 for d in docs if d.status == "incomplete")
    issues_files = sum(1 for d in docs if d.status == "missing")
    can_submit = issues_fields == 0 and issues_files == 0

    items = []
    for d in docs:
        ui = STATUS_UI.get(d.status, STATUS_UI["missing"])
        items.append(
            {
                "id": d.id,
                "document_type": d.document_type,
                "title": DOC_TITLES.get(d.document_type, d.document_type),
                "status": d.status,
                "status_label": ui["label"],
                "status_tone": ui["tone"],
                "updated_at": d.updated_at,
                "updated_label": _msk_label(d.updated_at),
                "action_label": _action_for(d.status),
                "required": d.required,
                "disclaimer": d.disclaimer,
                "payload": d.payload or {},
            }
        )

    fixes = _build_fixes(docs)

    history_rows = []
    for d in docs:
        for h in sorted(d.history, key=lambda x: x.changed_at, reverse=True):
            history_rows.append(
                {
                    "document_id": d.id,
                    "document_title": DOC_TITLES.get(d.document_type, d.document_type),
                    "status": h.status,
                    "note": h.note,
                    "changed_at": h.changed_at,
                    "changed_label": _msk_label(h.changed_at),
                    "actor": h.actor,
                }
            )
    history_rows.sort(key=lambda x: x["changed_at"], reverse=True)

    return {
        "shipment_id": shipment.id,
        "reference": shipment.reference,
        "route_label": f"{shipment.route_from} → {shipment.route_to}",
        "completeness_label": f"{ready} из {len(required)} документов",
        "completeness": round(ready / len(required), 2) if required else 1.0,
        "attention_label": f"{issues_fields} поле · {issues_files} файл",
        "attention_fields": issues_fields,
        "attention_files": issues_files,
        "can_submit_precheck": can_submit,
        "submit_hint": None
        if can_submit
        else "Сначала исправьте поля и добавьте недостающие файлы.",
        "banner": {
            "title": "ⓘ Тестовая интеграция",
            "text": (
                "Предварительная проверка выявляет ошибки в данных. "
                "Статус «Проверен» не является разрешением таможни."
            ),
        },
        "documents": items,
        "fixes": fixes,
        "history": history_rows[:12],
        "disclaimer": "Тестовый статус. Не является таможенным разрешением.",
        "data_quality": "synthetic_demo",
    }


async def analytics_dashboard(session: AsyncSession) -> dict:
    rows = (
        await session.execute(
            select(Shipment).options(selectinload(Shipment.documents), selectinload(Shipment.legs))
        )
    ).scalars().all()
    metrics = evaluate_models()
    delayed = [s for s in rows if s.delay_hours > 0]
    at_risk = [s for s in rows if s.risk_level in {"high", "medium"}]
    co2 = round(sum(float(s.co2e_tonnes or 0) for s in rows), 2)
    cost = round(sum(float(s.cost_rub or 0) for s in rows), 0)
    return {
        "title": "Аналитика коридора",
        "subtitle": "Каспийское звено · оперативные KPI",
        "kpis": {
            "shipments": len(rows),
            "delayed": len(delayed),
            "at_risk": len(at_risk),
            "avg_delay_hours": round(sum(s.delay_hours for s in rows) / len(rows), 1) if rows else 0,
            "co2e_tonnes": co2,
            "cost_rub": cost,
        },
        "model": {
            "mae_hours": metrics,
            "note": "Ошибка прогноза на holdout-выборке (MAE, часы).",
            "split": "time-based 70/30",
        },
        "shipments": [shipment_summary(s) for s in rows],
        "data_quality": "operational",
        "disclaimer": "Метрики коридора для диспетчерского контроля.",
    }


def _load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            return {**_DEFAULT_SETTINGS, **data}
        except Exception:
            pass
    return dict(_DEFAULT_SETTINGS)


def _save_settings(data: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_settings_payload() -> dict:
    return {
        **_load_settings(),
        "data_quality": "synthetic_demo",
        "disclaimer": "Настройки MVP сохраняются в backend/data/app_settings.json.",
    }


def update_settings_payload(patch: dict) -> dict:
    current = _load_settings()
    allowed = set(_DEFAULT_SETTINGS.keys()) - {"api_key_hint"}
    for k, v in patch.items():
        if k in allowed:
            current[k] = v
    _save_settings(current)
    return get_settings_payload()


async def fix_document_field(
    session: AsyncSession,
    document_id: str,
    *,
    hs_code: str | None = None,
    mark_file_added: bool = False,
    file_name: str | None = None,
) -> Document:
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one()
    return await add_or_update_document(
        session,
        shipment_id=doc.shipment_id,
        document_id=document_id,
        hs_code=hs_code,
        file_name=file_name or ("insurance_demo.pdf" if mark_file_added else None),
        mark_complete=False,
    )


async def submit_precheck(session: AsyncSession, shipment_id: str) -> dict:
    workspace = await documents_workspace(session, shipment_id)
    if not workspace["can_submit_precheck"]:
        return {
            "ok": False,
            "message": workspace["submit_hint"],
            "data_quality": "synthetic_demo",
        }
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Shipment)
        .where((Shipment.id == shipment_id) | (Shipment.reference == shipment_id))
        .options(selectinload(Shipment.documents))
    )
    shipment = result.scalar_one()
    for d in shipment.documents:
        if d.status in {"submitted", "accepted_for_review", "complete"}:
            prev = d.status
            d.status = "accepted_for_review" if prev != "complete" else "complete"
            d.updated_at = now
            session.add(
                DocumentStatusHistory(
                    id=f"dsh_{uuid.uuid4().hex[:10]}",
                    document_id=d.id,
                    status=d.status,
                    note="Пакет отправлен на предварительную проверку (тест)",
                    changed_at=now,
                    actor="api:precheck",
                )
            )
    await session.commit()
    return {
        "ok": True,
        "message": "Пакет отправлен на предварительную проверку (тестовый сервис).",
        "disclaimer": "Не является таможенным разрешением.",
        "data_quality": "synthetic_demo",
    }


async def compare_shipments(session: AsyncSession, shipment_ids: list[str]) -> dict:
    rows = (
        await session.execute(
            select(Shipment)
            .options(selectinload(Shipment.documents), selectinload(Shipment.legs))
            .order_by(Shipment.reference)
        )
    ).scalars().all()
    if shipment_ids:
        wanted = set(shipment_ids)
        rows = [s for s in rows if s.id in wanted or s.reference in wanted]

    if not rows:
        return {
            "title": "Сравнение перевозок",
            "subtitle": "Выберите минимум 2 груза",
            "columns": [],
            "metrics": [],
            "ranking": [],
            "insights": [],
            "winner_id": None,
            "data_quality": "synthetic_demo",
            "disclaimer": "Нет данных для сравнения.",
        }

    risk_score = {"low": 1.0, "medium": 0.55, "high": 0.2}
    columns = []
    for s in rows:
        required = [d for d in s.documents if d.required]
        ready = sum(1 for d in required if d.status != "missing")
        issues = sum(1 for d in required if d.status in {"missing", "incomplete"})
        docs_score = (ready / len(required)) if required else 1.0
        delay = float(s.delay_hours or 0)
        time_score = max(0.0, 1.0 - delay / 36.0)
        cost = float(s.cost_rub or 1)
        co2 = float(s.co2e_tonnes or 0.1)
        columns.append(
            {
                "shipment_id": s.id,
                "reference": s.reference,
                "route_from": s.route_from,
                "route_to": s.route_to,
                "route_label": f"{s.route_from} → {s.route_to}",
                "cargo": s.cargo_description,
                "container_no": s.container_no,
                "current_stage": s.current_stage,
                "planned_eta": s.planned_eta,
                "predicted_eta": s.predicted_eta,
                "delay_hours": delay,
                "delay_label": f"+{int(delay)} ч" if delay else "По плану",
                "risk_level": s.risk_level,
                "cost_rub": cost,
                "cost_label": f"{int(cost):,}".replace(",", " ") + " ₽",
                "co2e_tonnes": co2,
                "co2e_label": f"{co2:.2f} т".replace(".", ","),
                "documents_label": f"{ready} из {len(required) or 5}",
                "documents_issues": issues,
                "documents_score": round(docs_score, 2),
                "legs_count": len(s.legs),
                "missed_connection": s.missed_connection,
                "active_scenario": s.active_scenario,
                "_scores": {
                    "time": time_score,
                    "risk": risk_score.get(s.risk_level, 0.5),
                    "docs": docs_score,
                    "cost": 0.0,  # filled after normalize
                    "co2": 0.0,
                },
            }
        )

    max_cost = max(c["cost_rub"] for c in columns) or 1
    max_co2 = max(c["co2e_tonnes"] for c in columns) or 1
    for c in columns:
        c["_scores"]["cost"] = 1.0 - (c["cost_rub"] / max_cost) * 0.85
        c["_scores"]["co2"] = 1.0 - (c["co2e_tonnes"] / max_co2) * 0.85
        # weighted total 0..100
        sc = c["_scores"]
        total = (
            sc["time"] * 0.30
            + sc["risk"] * 0.20
            + sc["docs"] * 0.20
            + sc["cost"] * 0.15
            + sc["co2"] * 0.15
        )
        c["score"] = int(round(total * 100))
        c["score_breakdown"] = {
            "time": int(round(sc["time"] * 100)),
            "risk": int(round(sc["risk"] * 100)),
            "docs": int(round(sc["docs"] * 100)),
            "cost": int(round(sc["cost"] * 100)),
            "co2": int(round(sc["co2"] * 100)),
        }
        del c["_scores"]

    ranking = sorted(columns, key=lambda c: c["score"], reverse=True)
    for i, c in enumerate(ranking):
        c["rank"] = i + 1
    winner = ranking[0] if ranking else None

    metrics = [
        {"key": "delay_label", "label": "Отклонение от плана", "better": "lower_delay"},
        {"key": "risk_level", "label": "Уровень риска", "better": "lower_risk"},
        {"key": "cost_label", "label": "Стоимость", "better": "lower_cost"},
        {"key": "co2e_label", "label": "CO₂e", "better": "lower_co2"},
        {"key": "documents_label", "label": "Документы", "better": "higher_docs"},
        {"key": "current_stage", "label": "Текущий этап", "better": None},
        {"key": "legs_count", "label": "Число плеч", "better": None},
        {"key": "score", "label": "Итоговый балл", "better": "higher_score"},
    ]

    insights = []
    if winner:
        insights.append(
            {
                "code": "winner",
                "title": f"Лучший баланс: {winner['reference']}",
                "detail": f"Балл {winner['score']}/100 · {winner['route_label']}",
            }
        )
    fastest = min(columns, key=lambda c: (c["delay_hours"], c["cost_rub"]))
    cheapest = min(columns, key=lambda c: c["cost_rub"])
    cleanest = min(columns, key=lambda c: c["co2e_tonnes"])
    insights.extend(
        [
            {
                "code": "fastest",
                "title": f"Ближе к плану: {fastest['reference']}",
                "detail": fastest["delay_label"],
            },
            {
                "code": "cheapest",
                "title": f"Дешевле: {cheapest['reference']}",
                "detail": cheapest["cost_label"],
            },
            {
                "code": "cleanest",
                "title": f"Ниже CO₂e: {cleanest['reference']}",
                "detail": cleanest["co2e_label"],
            },
        ]
    )

    return {
        "title": "Сравнение перевозок",
        "subtitle": f"Выбрано грузов: {len(columns)} · баллы 0–100 по времени/риску/документам/цене/CO₂e",
        "columns": ranking,
        "metrics": metrics,
        "ranking": [{"shipment_id": c["shipment_id"], "reference": c["reference"], "score": c["score"], "rank": c["rank"]} for c in ranking],
        "insights": insights,
        "winner_id": winner["shipment_id"] if winner else None,
        "data_quality": "synthetic_demo",
        "disclaimer": "Сравнение по синтетическим KPI MVP. Не коммерческое предложение.",
    }
