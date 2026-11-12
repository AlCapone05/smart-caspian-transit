"""Human-readable Telegram messages — зеркало данных веб-диспетчерской."""

from __future__ import annotations

from datetime import datetime


def fmt_eta(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        raw = str(iso).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%d.%m %H:%M")
    except Exception:
        return str(iso)[:16]


def fmt_overview(data: dict) -> str:
    """Как блок KPI + внимание на странице Обзор."""
    k = data.get("kpis") or {}
    title = data.get("title") or "Обзор"
    subtitle = data.get("subtitle") or ""
    lines = [
        f"📋 *{title}*",
        subtitle,
        "",
        f"Активные перевозки: *{k.get('active', '—')}*",
        f"△ Под риском: *{k.get('at_risk', '—')}*",
        f"! Задержаны: *{k.get('delayed', '—')}*",
        f"Ожидают документов: *{k.get('awaiting_docs', '—')}*",
    ]
    if data.get("selected_map_reference"):
        lines.append(f"Карта · фокус: `{data['selected_map_reference']}`")
    attn = data.get("attention") or []
    if attn:
        lines.append("")
        lines.append("*Требуют внимания (с сайта):*")
        for a in attn[:5]:
            title_a = a.get("title") or a.get("attention_title") or "—"
            detail = a.get("detail") or a.get("attention_detail") or ""
            lines.append(f"• {title_a}")
            if detail:
                lines.append(f"  _{detail[:160]}_")
    ships = data.get("shipments") or []
    if ships:
        lines.append("")
        lines.append("*Грузы с сайта:*")
        for s in ships[:8]:
            delay = s.get("delay_hours") or 0
            mark = "△" if s.get("risk_level") in {"high", "medium"} or delay > 0 else "•"
            docs = s.get("documents_label") or ""
            lines.append(
                f"{mark} `{s.get('reference')}` · {s.get('route_label')} · {s.get('current_stage')}"
            )
            lines.append(f"  ETA {fmt_eta(s.get('predicted_eta'))} · {docs}")
    if data.get("disclaimer"):
        lines.extend(["", f"_{data['disclaimer']}_"])
    return "\n".join(lines)


def fmt_shipment(d: dict) -> str:
    """Карточка груза как на сайте."""
    delay = d.get("delay_hours") or 0
    delay_s = "в плане" if delay <= 0 else f"+{delay:.0f} ч к плану"
    docs_ready = d.get("documents_ready")
    docs_total = d.get("documents_total")
    docs = f"{docs_ready} из {docs_total}" if docs_ready is not None else "—"
    lines = [
        f"📦 *{d.get('reference', '—')}*",
        d.get("route_label")
        or f"{d.get('route_from', '')} → {d.get('route_to', '')}",
        d.get("cargo_line") or d.get("cargo_description") or "",
        "",
        f"Этап: *{d.get('current_stage', '—')}*",
        f"Локация: {d.get('current_location', '—')}",
        f"Статус: `{d.get('status', '—')}` · риск: `{d.get('risk_level', '—')}`",
        f"План ETA: {fmt_eta(d.get('planned_eta'))}",
        f"Прогноз: *{fmt_eta(d.get('predicted_eta'))}* ({delay_s})",
        f"Документы: {docs}",
        f"Стоимость: {d.get('cost_rub', '—')} ₽ · CO₂e: {d.get('co2e_tonnes', '—')} т",
    ]
    if d.get("risk_headline"):
        lines.extend(["", f"⚠ *{d['risk_headline']}*"])
        if d.get("risk_detail"):
            lines.append(d["risk_detail"])
    legs = d.get("legs") or []
    if legs:
        lines.append("")
        lines.append("*Плечи (с сайта):*")
        for leg in legs[:6]:
            badge = leg.get("stage_status_label") or leg.get("status") or ""
            lines.append(
                f"• {leg.get('label') or leg.get('mode')}: "
                f"{leg.get('origin_name')} → {leg.get('destination_name')} · {badge}"
            )
    timeline = d.get("timeline") or []
    if timeline:
        lines.append("")
        lines.append("*Таймлайн:*")
        for e in timeline[:4]:
            lines.append(f"• {fmt_eta(e.get('occurred_at'))} — {e.get('title') or e.get('event_type')}")
    missing = (d.get("documents") or {}).get("missing") or []
    if missing:
        lines.append("")
        lines.append("Документы △: " + ", ".join(missing[:6]))
    if d.get("schedule_disclaimer"):
        lines.extend(["", f"_{d['schedule_disclaimer']}_"])
    return "\n".join(lines)


def fmt_alerts(notifs: dict, track_alerts: dict | None = None) -> str:
    items = notifs.get("items") or []
    lines = ["🔔 *Уведомления с сайта*", ""]
    if notifs.get("enabled") is False:
        lines.append("_Уведомления выключены в настройках сайта._")
        lines.append("")
    if not items:
        lines.append("Событий пока нет.")
    else:
        for n in items[:12]:
            kind = n.get("kind") or "info"
            mark = {"weather": "🌩", "docs": "📄", "risk": "△"}.get(kind, "•")
            lines.append(f"{mark} *{n.get('title', '—')}*")
            if n.get("detail"):
                lines.append(f"  {n['detail']}")
            meta = []
            if n.get("reference"):
                meta.append(f"`{n['reference']}`")
            if n.get("created_label"):
                meta.append(n["created_label"])
            if meta:
                lines.append("  " + " · ".join(meta))
            lines.append("")
    weather = (track_alerts or {}).get("items") or []
    if weather:
        lines.append("*Погода / штормы (трекер сайта):*")
        for a in weather[:6]:
            sev = a.get("severity") or ""
            lines.append(f"• [{sev}] {a.get('title') or a.get('kind')}")
            if a.get("detail"):
                lines.append(f"  {a['detail'][:140]}")
    disc = notifs.get("disclaimer") or (track_alerts or {}).get("disclaimer")
    if disc:
        lines.extend(["", f"_{disc}_"])
    return "\n".join(lines)


def fmt_storms(track: dict) -> str:
    cells = track.get("storm_cells") or []
    affected = track.get("storm_affected_vessel_ids") or []
    k = track.get("kpis") or {}
    lines = [
        f"🌩 *{track.get('title') or 'GPS-трекер · Каспий'}*",
        track.get("subtitle") or "",
        "",
        f"Судов: {k.get('vessels', '—')} · в пути: {k.get('underway', '—')} · алертов: {k.get('alerts', '—')}",
        "",
    ]
    if not cells:
        lines.append("Штормовых ячеек нет.")
    else:
        lines.append("*Live-штормы с карты сайта:*")
        for c in cells[:8]:
            wind = c.get("wind_ms")
            wind_s = f"{wind:.0f} м/с" if isinstance(wind, (int, float)) else "—"
            lines.append(
                f"• *{c.get('name') or c.get('id')}* · {wind_s} · R≈{round(c.get('radius_km') or 0)} км"
            )
    vessels = track.get("vessels") or []
    hit = [v for v in vessels if v.get("id") in set(affected)]
    if hit:
        lines.append("")
        lines.append("*Суда в зоне (с сайта):*")
        for v in hit:
            lines.append(f"• {v.get('name')} · {v.get('route_label')} · {v.get('progress_pct', '?')}%")
            if v.get("shipment_id"):
                lines.append(f"  груз id: `{v.get('shipment_id')}`")
    else:
        lines.append("")
        lines.append("*Суда на карте:*")
        for v in vessels[:6]:
            lines.append(
                f"• {v.get('name')} · {v.get('status_label') or v.get('status')} · {v.get('route_label')}"
            )
    if track.get("disclaimer"):
        lines.extend(["", f"_{track['disclaimer']}_"])
    return "\n".join(lines)


def fmt_alternatives(data: dict) -> str:
    lines = [
        f"🛤 *Обходы · {data.get('reference') or data.get('shipment_id')}*",
        data.get("route_label") or "",
        "",
    ]
    insight = data.get("insight") or {}
    if insight.get("title"):
        lines.append(f"💡 {insight['title']}")
        if insight.get("detail"):
            lines.append(insight["detail"])
        lines.append("")
    for a in data.get("alternatives") or []:
        mark = "✅" if a.get("recommended") else ("◎" if a.get("is_current") else "○")
        feas = "" if a.get("feasible") else " · недоступен"
        lines.append(f"{mark} *{a.get('title')}*{feas}")
        bits = [x for x in (a.get("eta_label"), a.get("cost_label"), a.get("co2e_label")) if x]
        if bits:
            lines.append("  " + " · ".join(bits))
        if a.get("description"):
            lines.append(f"  _{a['description'][:140]}_")
        if a.get("infeasible_reason"):
            lines.append(f"  _{a['infeasible_reason']}_")
        lines.append("")
    if data.get("footnote"):
        lines.append(f"_{data['footnote']}_")
    return "\n".join(lines)


def fmt_push_item(n: dict) -> str:
    kind = n.get("kind") or "info"
    mark = {"weather": "🌩", "docs": "📄", "risk": "△", "storm": "🌩"}.get(kind, "🔔")
    lines = [
        f"{mark} *Новое с сайта*",
        f"*{n.get('title', 'Событие')}*",
    ]
    if n.get("detail"):
        lines.append(n["detail"])
    if n.get("reference"):
        lines.append(f"Груз: `{n['reference']}`")
    if n.get("created_label"):
        lines.append(n["created_label"])
    return "\n".join(lines)
