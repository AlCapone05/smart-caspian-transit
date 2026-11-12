"""SCT project-scoped dispatcher assistant (refuses off-topic)."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Shipment
from app.services.live_storms import get_cells
from app.services.tracking import tracking_dashboard

OFFTOPIC_REPLY = (
    "Я ассистент только по Smart Caspian Transit. "
    "Могу помочь с перевозками, картой/GPS, штормами и обходами, документами, "
    "сравнением грузов, альтернативами маршрута, аналитикой и настройками. "
    "Запросы вне проекта не обрабатываю."
)

PROJECT_KEYWORDS = [
    "sct",
    "каспи",
    "caspian",
    "перевоз",
    "груз",
    "контейнер",
    "маршрут",
    "обход",
    "альтернатив",
    "шторм",
    "погод",
    "ветер",
    "волнен",
    "судно",
    "корабл",
    "gps",
    "трекер",
    "карта",
    "порт",
    "астрахан",
    "энзел",
    "махачкал",
    "актау",
    "баку",
    "документ",
    "тн вэд",
    "тнвэд",
    "eta",
    "задерж",
    "риск",
    "стыков",
    "сравнен",
    "аналитик",
    "настройк",
    "диспетч",
    "логист",
    "co2",
    "со2",
    "стоимост",
    "тариф",
    "сценари",
    "симуляц",
    "проект",
    "как работ",
    "что умеет",
    "помощь",
    "help",
    "что ты",
    "кто ты",
]

GREETINGS = {"привет", "здравствуй", "здравствуйте", "добрый", "hi", "hello", "хай"}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def is_on_topic(message: str) -> bool:
    t = _norm(message)
    if not t:
        return False
    words = set(re.findall(r"[a-zа-яё0-9\-]+", t, flags=re.I))
    if words & GREETINGS and len(words) <= 3:
        return True
    if "sct-" in t or re.search(r"\bsct\b", t):
        return True
    return any(k in t for k in PROJECT_KEYWORDS)


async def _project_context(session: AsyncSession) -> dict:
    track = await tracking_dashboard(session)
    rows = (
        await session.execute(
            select(Shipment).options(selectinload(Shipment.documents)).order_by(Shipment.reference)
        )
    ).scalars().all()
    shipments = []
    attention = []
    for s in rows:
        docs = [d for d in s.documents if d.required]
        ready = sum(1 for d in docs if d.status != "missing")
        shipments.append(
            {
                "reference": s.reference,
                "route": f"{s.route_from} → {s.route_to}",
                "stage": s.current_stage,
                "delay_hours": s.delay_hours,
                "risk": s.risk_level,
                "docs": f"{ready}/{len(docs) or 5}",
                "alt": s.selected_alternative_id,
                "attention": s.attention_title,
            }
        )
        if s.attention_title:
            attention.append(
                {
                    "reference": s.reference,
                    "title": s.attention_title,
                    "detail": s.attention_detail,
                }
            )
    active = sum(1 for s in rows if s.status not in {"delivered", "cancelled"})
    at_risk = sum(1 for s in rows if s.risk_level in {"high", "medium"})
    delayed = sum(1 for s in rows if (s.delay_hours or 0) > 0)
    awaiting_docs = sum(
        1
        for s in rows
        if any(d.required and d.status in {"missing", "incomplete"} for d in s.documents)
    )
    cells = get_cells()
    return {
        "overview_kpis": {
            "active": active,
            "at_risk": at_risk,
            "delayed": delayed,
            "awaiting_docs": awaiting_docs,
        },
        "attention": attention[:3],
        "shipments": shipments,
        "vessels": [
            {
                "name": v["name"],
                "route": v["route_label"],
                "status": v["status_label"],
                "progress_pct": v["progress_pct"],
                "lat": v["lat"],
                "lon": v["lon"],
            }
            for v in track.get("vessels", [])
        ],
        "storm_cells": [
            {
                "name": c.get("name"),
                "lat": c.get("lat"),
                "lon": c.get("lon"),
                "wind_ms": c.get("wind_ms"),
                "severity": c.get("severity"),
                "radius_km": c.get("radius_km"),
            }
            for c in cells
        ],
        "storm_affected": track.get("storm_affected_vessel_ids") or [],
    }


def _local_answer(message: str, ctx: dict) -> str:
    t = _norm(message)
    words = set(re.findall(r"[a-zа-яё0-9\-]+", t, flags=re.I))

    if words & GREETINGS and len(t) < 40:
        return (
            "Здравствуйте. Я SCT-ассистент диспетчерской Smart Caspian Transit. "
            "Спросите про груз (например SCT-2048), штормы на карте, обход маршрута, "
            "документы или сравнение перевозок."
        )

    if any(k in t for k in ("кто ты", "что ты", "помощь", "help", "что умеешь", "как работ", "проект")):
        return (
            "Smart Caspian Transit — демо-диспетчерская каспийского звена коридора «Север — Юг». "
            "Я помогаю только по проекту:\n"
            "• перевозки и риски (SCT-…)\n"
            "• live GPS / карта / штормы и обходы\n"
            "• документы (пакет из 5)\n"
            "• сравнение грузов и альтернативы маршрута\n"
            "• аналитика и настройки\n"
            "Данные синтетические; статусы документов — не таможенное разрешение."
        )

    # Specific shipment
    m = re.search(r"sct[-\s]?(\d{3,5})", t, flags=re.I)
    if m:
        ref = f"SCT-{m.group(1)}"
        hit = next((s for s in ctx["shipments"] if s["reference"].upper() == ref.upper()), None)
        if not hit:
            refs = ", ".join(s["reference"] for s in ctx["shipments"]) or "нет"
            return f"Груз {ref} не найден. Сейчас в системе: {refs}."
        alt = hit["alt"] or "прямой / не выбран"
        att = hit["attention"] or "без отдельного внимания"
        return (
            f"{hit['reference']}: {hit['route']}.\n"
            f"Этап: {hit['stage']}. Риск: {hit['risk']}. "
            f"Отклонение: {'+' + str(int(hit['delay_hours'])) + ' ч' if hit['delay_hours'] else 'по плану'}.\n"
            f"Документы: {hit['docs']}. Альтернатива: {alt}.\n"
            f"Внимание: {att}."
        )

    if any(k in t for k in ("шторм", "погод", "ветер", "волнен")):
        cells = ctx["storm_cells"]
        if not cells:
            return "Сейчас live-ячеек шторма нет в кэше. Включите Live на Обзоре — погода обновляется раз в ~2–3 минуты."
        lines = [
            f"• {c['name']}: {c['wind_ms']} м/с, R≈{c['radius_km']} км, "
            f"{c['lat']}°N {c['lon']}°E, индекс {c['severity']}"
            for c in cells[:5]
        ]
        affected = ctx.get("storm_affected") or []
        extra = f"\nЗатронуты суда (id): {', '.join(affected)}" if affected else ""
        return (
            "Live-штормы на Каспии (двигаются ~каждые 2–3 мин):\n"
            + "\n".join(lines)
            + extra
            + "\nЕсли судно в зоне — на Обзоре доступен выбор обхода (Махачкала / Актау)."
        )

    if any(k in t for k in ("обход", "альтернатив", "маршрут")):
        return (
            "Альтернативные пути:\n"
            "1) Обзор → клик по судну в зоне шторма → «На карте» / «Выбрать».\n"
            "2) Перевозки → карточка груза → «Сравнить альтернативы» "
            "(текущий / через Махачкалу / через Актау).\n"
            "Выбор обновляет ETA, стоимость, CO₂e и линию маршрута на карте."
        )

    if any(k in t for k in ("судн", "корабл", "gps", "трекер", "карта")):
        vessels = ctx["vessels"]
        if not vessels:
            return "Данных трекера сейчас нет. Откройте Обзор и включите Live."
        lines = [
            f"• {v['name']}: {v['route']} — {v['status']} ({v['progress_pct']}%)"
            for v in vessels
        ]
        return "Суда на карте:\n" + "\n".join(lines) + "\nКарта: компактная на Обзоре, полная — кнопка «Открыть карту»."

    if any(k in t for k in ("документ", "тн вэд", "тнвэд", "pre-check", "precheck")):
        return (
            "Документы: пакет из 5 типов на перевозку. "
            "Откройте вкладку «Документы», выберите груз, добавьте PDF / исправьте ТН ВЭД "
            "и отправьте тестовый pre-check. "
            "Статус не является таможенным разрешением."
        )

    if any(k in t for k in ("сравнен", "compare")):
        return (
            "Сравнение: вкладка «Сравнение» или «Сравнить» в списке перевозок (отметьте ≥2 груза). "
            "Баллы 0–100 по времени / риску / документам / цене / CO₂e."
        )

    if any(k in t for k in ("риск", "задерж", "вниман", "проблем")):
        att = ctx.get("attention") or []
        if not att:
            kpis = ctx.get("overview_kpis") or {}
            return (
                f"Сводка KPI: активных {kpis.get('active', '—')}, "
                f"под риском {kpis.get('at_risk', '—')}, "
                f"задержаны {kpis.get('delayed', '—')}, "
                f"ждут документы {kpis.get('awaiting_docs', '—')}."
            )
        lines = [f"• {a.get('reference')}: {a.get('title')} — {a.get('detail')}" for a in att]
        return "Сейчас требуют внимания:\n" + "\n".join(lines)

    if any(k in t for k in ("аналитик", "kpi", "настройк")):
        return (
            "Аналитика — KPI коридора и качество модели. "
            "Настройки — часовой пояс, уведомления, сценарий по умолчанию, неопределённость CO₂e."
        )

    # Generic on-topic fallback with live snapshot
    kpis = ctx.get("overview_kpis") or {}
    refs = ", ".join(s["reference"] for s in ctx["shipments"][:5]) or "—"
    return (
        "Краткий статус SCT:\n"
        f"• Активных: {kpis.get('active', '—')}, риск: {kpis.get('at_risk', '—')}, "
        f"задержки: {kpis.get('delayed', '—')}\n"
        f"• Грузы: {refs}\n"
        f"• Штормовых ячеек: {len(ctx.get('storm_cells') or [])}\n"
        "Уточните: груз SCT-…, шторм, обход, документы или сравнение."
    )


SYSTEM_PROMPT = (
    "Ты — SCT-агент поддержки диспетчерской Smart Caspian Transit "
    "(каспийское звено коридора «Север — Юг»).\n"
    "ЖЁСТКИЕ ПРАВИЛА:\n"
    "1) Отвечай ТОЛЬКО по этому проекту: перевозки SCT, карта/GPS, суда, порты Каспия, "
    "live-штормы и обходы, документы, сравнение грузов, альтернативы маршрута, "
    "аналитика, настройки, сценарии симуляции.\n"
    "2) Любой вопрос вне проекта (рецепты, политика, учёба, код не по SCT, шутки, "
    "общие знания) — НЕ отвечай по сути. Ответь одной фразой отказа: "
    "«Работаю только по Smart Caspian Transit — задайте вопрос о перевозках, карте, "
    "штормах, документах или сравнении.»\n"
    "3) Опирайся на CONTEXT; данные синтетические (демо). "
    "Не выдумывай реальные рейсы/таможню.\n"
    "4) Отвечай по-русски, кратко и по делу."
)


def _resolve_llm() -> tuple[str, str, str, str] | None:
    """Return (provider, base_url, api_key, model)."""
    from app.config import get_settings

    s = get_settings()
    provider = (s.assistant_provider or "deepseek").strip().lower()

    deepseek_key = (
        s.deepseek_api_key
        or os.getenv("DEEPSEEK_API_KEY", "")
        or os.getenv("SCT_ASSISTANT_API_KEY", "")
    ).strip()
    openai_key = (s.openai_api_key or os.getenv("OPENAI_API_KEY", "")).strip()

    if provider in {"local", "off", "none"}:
        return None

    if provider == "deepseek" or (provider == "auto" and deepseek_key):
        if not deepseek_key:
            return None
        base = (s.deepseek_base_url or "https://api.deepseek.com").rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        model = (s.assistant_model or s.deepseek_model or "deepseek-chat").strip()
        return ("deepseek", base, deepseek_key, model)

    if provider == "openai" or (provider == "auto" and openai_key):
        if not openai_key:
            return None
        base = (s.openai_base_url or "https://api.openai.com/v1").rstrip("/")
        model = (s.assistant_model or s.openai_model or "gpt-4o-mini").strip()
        return ("openai", base, openai_key, model)

    if deepseek_key:
        base = (s.deepseek_base_url or "https://api.deepseek.com").rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        model = (s.assistant_model or s.deepseek_model or "deepseek-chat").strip()
        return ("deepseek", base, deepseek_key, model)
    if openai_key:
        base = (s.openai_base_url or "https://api.openai.com/v1").rstrip("/")
        model = (s.assistant_model or s.openai_model or "gpt-4o-mini").strip()
        return ("openai", base, openai_key, model)
    return None


async def _llm_answer(message: str, ctx: dict, history: list[dict] | None = None) -> tuple[str, str] | None:
    """Call DeepSeek/OpenAI. Returns (reply, provider) or None."""
    resolved = _resolve_llm()
    if not resolved:
        return None
    provider, base, api_key, model = resolved

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for h in history[-6:]:
            role = h.get("role")
            content = (h.get("content") or h.get("text") or "").strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content[:2000]})
    messages.append(
        {
            "role": "user",
            "content": f"CONTEXT (JSON):\n{ctx}\n\nQUESTION:\n{message}",
        }
    )
    payload = {"model": model, "temperature": 0.15, "messages": messages}

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            res = await client.post(
                f"{base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            res.raise_for_status()
            data = res.json()
            text = (data["choices"][0]["message"]["content"] or "").strip()
            if not text:
                return None
            return text, provider
    except Exception:
        return None


def _looks_like_refusal(text: str) -> bool:
    low = text.lower()
    markers = (
        "только по smart caspian",
        "работаю только по",
        "вне проекта",
        "не обрабатываю",
        "задайте вопрос о перевозках",
    )
    return any(m in low for m in markers)


async def chat(session: AsyncSession, message: str, history: list[dict] | None = None) -> dict:
    text = (message or "").strip()
    if not text:
        return {
            "ok": False,
            "refused": True,
            "reply": "Напишите вопрос по Smart Caspian Transit.",
            "mode": "gate",
            "provider": "gate",
        }

    # Hard gate: off-topic never reaches DeepSeek
    if not is_on_topic(text):
        return {
            "ok": True,
            "refused": True,
            "reply": OFFTOPIC_REPLY,
            "mode": "gate",
            "provider": "gate",
        }

    ctx = await _project_context(session)
    llm = await _llm_answer(text, ctx, history)
    if llm:
        reply, provider = llm
        refused = _looks_like_refusal(reply)
        return {
            "ok": True,
            "refused": refused,
            "reply": reply,
            "mode": "llm",
            "provider": provider,
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "ok": True,
        "refused": False,
        "reply": _local_answer(text, ctx),
        "mode": "local",
        "provider": "local",
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
