"""МОГГНИТ Telegram bot — long polling на httpx (без лишних зависимостей)."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from tg_bot.api_client import SctApi
from tg_bot.formatters import (
    fmt_alerts,
    fmt_alternatives,
    fmt_overview,
    fmt_push_item,
    fmt_shipment,
    fmt_storms,
)
from tg_bot import subscribers

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("moggnit.tg")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

REF_RE = re.compile(r"\b(SCT-[\w-]+|shp_[\w]+)\b", re.I)

HELP = (
    "🤖 МОГГНИТ · данные с диспетчерской\n"
    "Бот читает тот же API, что и сайт.\n\n"
    "Команды:\n"
    "/start — меню\n"
    "/summary — Обзор с сайта (KPI + грузы)\n"
    "/alerts — уведомления сайта\n"
    "/storms — карта/штормы с сайта\n"
    "/status SCT-2048 — карточка груза\n"
    "/routes SCT-2048 — обходы\n"
    "/list — список перевозок\n"
    "/subscribe — пуш новых событий с сайта\n"
    "/unsubscribe — отключить пуш\n\n"
    "Или пришлите SCT-XXXX / вопрос по проекту."
)

MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "📋 Сводка"}, {"text": "🔔 Алерты"}],
        [{"text": "🌩 Штормы"}, {"text": "📦 Грузы"}],
        [{"text": "📡 Подписка"}, {"text": "❓ Помощь"}],
    ],
    "resize_keyboard": True,
}

SYNC_INTERVAL_SEC = float(os.getenv("TG_SYNC_INTERVAL_SEC", "20"))


class TgBot:
    def __init__(self, token: str, api: SctApi) -> None:
        self.token = token
        self.api = api
        self.base = f"https://api.telegram.org/bot{token}"
        # trust_env=False — не брать системный HTTP(S)_PROXY (часто даёт 403 к api.telegram.org)
        self.client = httpx.AsyncClient(timeout=60.0, trust_env=False)
        self.offset = 0

    async def close(self) -> None:
        await self.client.aclose()

    async def call(self, method: str, payload: dict | None = None) -> dict:
        r = await self.client.post(f"{self.base}/{method}", json=payload or {})
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description") or str(data))
        return data["result"]

    async def send(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
        parse_mode: str | None = None,
    ) -> None:
        body: dict[str, Any] = {"chat_id": chat_id, "text": text[:3900]}
        if reply_markup:
            body["reply_markup"] = reply_markup
        if parse_mode:
            body["parse_mode"] = parse_mode
        try:
            await self.call("sendMessage", body)
        except Exception:
            # fallback without markdown if parse fails
            body.pop("parse_mode", None)
            await self.call("sendMessage", body)

    async def typing(self, chat_id: int) -> None:
        try:
            await self.call("sendChatAction", {"chat_id": chat_id, "action": "typing"})
        except Exception:
            pass

    async def handle_update(self, upd: dict) -> None:
        if "callback_query" in upd:
            await self.on_callback(upd["callback_query"])
            return
        msg = upd.get("message") or upd.get("edited_message")
        if not msg or "text" not in msg:
            return
        await self.on_message(msg)

    async def on_message(self, msg: dict) -> None:
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()
        if not text:
            return

        if text.startswith("/start") or text == "❓ Помощь" or text.startswith("/help"):
            await self.send(chat_id, HELP, reply_markup=MAIN_KEYBOARD)
            return

        if text.startswith("/subscribe") or text == "📡 Подписка":
            if subscribers.subscribe(chat_id):
                await self.send(
                    chat_id,
                    "📡 Подписка включена.\n"
                    "Новые уведомления и штормовые алерты с сайта будут приходить сюда.",
                    reply_markup=MAIN_KEYBOARD,
                )
            else:
                await self.send(chat_id, "Вы уже подписаны на пуш с сайта.", reply_markup=MAIN_KEYBOARD)
            return
        if text.startswith("/unsubscribe"):
            if subscribers.unsubscribe(chat_id):
                await self.send(chat_id, "Подписка отключена.", reply_markup=MAIN_KEYBOARD)
            else:
                await self.send(chat_id, "Вы не были подписаны.", reply_markup=MAIN_KEYBOARD)
            return

        if text.startswith("/summary") or text == "📋 Сводка":
            await self.cmd_summary(chat_id)
            return
        if text.startswith("/alerts") or text == "🔔 Алерты":
            await self.cmd_alerts(chat_id)
            return
        if text.startswith("/storms") or text == "🌩 Штормы":
            await self.cmd_storms(chat_id)
            return
        if text.startswith("/list") or text == "📦 Грузы":
            await self.cmd_list(chat_id)
            return
        if text.startswith("/status"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                await self.send(chat_id, "Пример: /status SCT-2048")
            else:
                await self.send_shipment(chat_id, parts[1].strip())
            return
        if text.startswith("/routes"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                await self.send(chat_id, "Пример: /routes SCT-2048")
            else:
                await self.send_routes(chat_id, parts[1].strip())
            return

        if re.fullmatch(r"SCT-[\w-]+", text, re.I) or re.fullmatch(r"shp_[\w]+", text, re.I):
            await self.send_shipment(chat_id, text)
            return

        m = REF_RE.search(text)
        if m and len(text) <= 48:
            await self.send_shipment(chat_id, m.group(1))
            return

        await self.typing(chat_id)
        try:
            res = await self.api.assistant(text)
            answer = res.get("reply") or res.get("answer") or res.get("text") or str(res)
            if res.get("refused"):
                answer = f"⛔ {answer}"
            await self.send(chat_id, answer)
        except Exception as e:
            await self.send(chat_id, f"Не понял запрос. Пришлите SCT-2048 или /help\n({e})")

    async def on_callback(self, cq: dict) -> None:
        data = cq.get("data") or ""
        chat_id = cq["message"]["chat"]["id"]
        cq_id = cq["id"]
        try:
            await self.call("answerCallbackQuery", {"callback_query_id": cq_id})
        except Exception:
            pass

        if data.startswith("ship:"):
            await self.send_shipment(chat_id, data.split(":", 1)[1])
        elif data.startswith("routes:"):
            await self.send_routes(chat_id, data.split(":", 1)[1])
        elif data.startswith("pick:"):
            raw = data[5:]
            ship_id, _, alt_id = raw.partition(":")
            try:
                res = await self.api.select_alternative(ship_id, alt_id)
                await self.send(
                    chat_id,
                    "✅ Маршрут обновлён\n"
                    f"ETA: {res.get('predicted_eta', '—')}\n"
                    f"Задержка: {res.get('delay_hours', '—')} ч\n"
                    f"Стоимость: {res.get('cost_rub', '—')} ₽",
                )
            except Exception as e:
                await self.send(chat_id, f"Не удалось выбрать обход: {e}")
        elif data.startswith("vroute:"):
            await self.send_vessel_routes(chat_id, data.split(":", 1)[1])
        elif data.startswith("vpick:"):
            raw = data[6:]
            vessel_id, _, alt_id = raw.partition(":")
            try:
                await self.api.select_vessel_route(vessel_id, alt_id)
                await self.send(chat_id, f"✅ Обход {alt_id} применён.")
            except Exception as e:
                await self.send(chat_id, f"Не удалось: {e}")

    async def cmd_summary(self, chat_id: int) -> None:
        try:
            data = await self.api.overview()
            await self.send(chat_id, fmt_overview(data), parse_mode="Markdown")
        except Exception as e:
            await self.send(chat_id, f"Не удалось получить сводку: {e}")

    async def cmd_alerts(self, chat_id: int) -> None:
        try:
            notifs = await self.api.notifications()
            weather = await self.api.tracking_alerts()
            await self.send(chat_id, fmt_alerts(notifs, weather), parse_mode="Markdown")
        except Exception as e:
            await self.send(chat_id, f"Не удалось получить алерты: {e}")

    async def cmd_storms(self, chat_id: int) -> None:
        try:
            track = await self.api.tracking()
            text = fmt_storms(track)
            rows = []
            affected = set(track.get("storm_affected_vessel_ids") or [])
            for v in track.get("vessels") or []:
                alts = v.get("storm_alternatives") or []
                if v.get("id") in affected and len(alts) > 1:
                    rows.append(
                        [{"text": f"Обход · {v.get('name', v['id'])}", "callback_data": f"vroute:{v['id']}"}]
                    )
            kb = {"inline_keyboard": rows} if rows else None
            await self.send(chat_id, text, reply_markup=kb, parse_mode="Markdown")
        except Exception as e:
            await self.send(chat_id, f"Не удалось получить штормы: {e}")

    async def cmd_list(self, chat_id: int) -> None:
        try:
            data = await self.api.list_shipments()
            items = data.get("items") or []
            if not items:
                await self.send(chat_id, "Грузов пока нет.")
                return
            lines = ["📦 Перевозки", ""]
            rows = []
            for s in items[:12]:
                delay = s.get("delay_hours") or 0
                mark = "△" if s.get("risk_level") in {"high", "medium"} or delay > 0 else "•"
                lines.append(
                    f"{mark} {s.get('reference')} · {s.get('route_label')} · {s.get('current_stage')}"
                )
                ref = s.get("reference") or s["id"]
                rows.append([{"text": ref, "callback_data": f"ship:{ref}"}])
            await self.send(chat_id, "\n".join(lines), reply_markup={"inline_keyboard": rows})
        except Exception as e:
            await self.send(chat_id, f"Не удалось получить список: {e}")

    async def send_shipment(self, chat_id: int, ref: str) -> None:
        try:
            d = await self.api.shipment(ref)
            kb = {
                "inline_keyboard": [
                    [
                        {
                            "text": "Обходы маршрута",
                            "callback_data": f"routes:{d.get('reference') or d['id']}",
                        }
                    ]
                ]
            }
            await self.send(chat_id, fmt_shipment(d), reply_markup=kb, parse_mode="Markdown")
        except Exception as e:
            await self.send(chat_id, f"Не найден / ошибка: {e}")

    async def send_routes(self, chat_id: int, ref: str) -> None:
        try:
            ship = await self.api.shipment(ref)
            data = await self.api.alternatives(ship["id"])
            rows = []
            for a in data.get("alternatives") or []:
                if not a.get("feasible"):
                    continue
                title = ("✓ " if a.get("is_current") else "") + (a.get("title") or a["id"])
                rows.append([{"text": title[:60], "callback_data": f"pick:{ship['id']}:{a['id']}"}])
            await self.send(
                chat_id,
                fmt_alternatives(data),
                reply_markup={"inline_keyboard": rows} if rows else None,
                parse_mode="Markdown",
            )
        except Exception as e:
            await self.send(chat_id, f"Не удалось получить обходы: {e}")

    async def send_vessel_routes(self, chat_id: int, vessel_id: str) -> None:
        try:
            track = await self.api.tracking()
            vessel = next((v for v in track.get("vessels") or [] if v["id"] == vessel_id), None)
            if not vessel:
                await self.send(chat_id, "Судно не найдено")
                return
            alts = vessel.get("storm_alternatives") or []
            lines = [f"🛤 Обходы для {vessel.get('name')}", vessel.get("route_label") or "", ""]
            rows = []
            for a in alts:
                lines.append(f"• {a.get('title') or a.get('id')}")
                if a.get("id"):
                    rows.append(
                        [
                            {
                                "text": (a.get("title") or a["id"])[:60],
                                "callback_data": f"vpick:{vessel_id}:{a['id']}",
                            }
                        ]
                    )
            await self.send(
                chat_id,
                "\n".join(lines),
                reply_markup={"inline_keyboard": rows} if rows else None,
            )
        except Exception as e:
            await self.send(chat_id, f"Ошибка: {e}")

    async def sync_site_once(self, *, bootstrap: bool = False) -> None:
        """Тянем уведомления/алерты сайта и пушим подписчикам новые события."""
        chats = subscribers.list_chats()
        if not chats and not bootstrap:
            return
        try:
            notifs = await self.api.notifications()
            weather = await self.api.tracking_alerts()
        except Exception as e:
            log.warning("site sync failed: %s", e)
            return

        items: list[dict] = []
        for n in notifs.get("items") or []:
            items.append(
                {
                    "id": str(n.get("id") or f"n_{n.get('title')}"),
                    "kind": n.get("kind") or "info",
                    "title": n.get("title"),
                    "detail": n.get("detail"),
                    "reference": n.get("reference"),
                    "created_label": n.get("created_label"),
                }
            )
        for a in weather.get("items") or []:
            items.append(
                {
                    "id": str(a.get("id") or f"w_{a.get('title')}"),
                    "kind": "weather",
                    "title": a.get("title") or a.get("kind"),
                    "detail": a.get("detail"),
                    "reference": None,
                    "created_label": None,
                }
            )

        seen = subscribers.get_seen()
        fresh = [x for x in items if x["id"] not in seen]
        if bootstrap:
            # при старте не спамим старым — только запоминаем
            subscribers.add_seen([x["id"] for x in items])
            log.info("site sync bootstrap: remembered %s events", len(items))
            return
        if not fresh:
            return
        for n in fresh:
            text = fmt_push_item(n)
            for chat_id in chats:
                try:
                    await self.send(chat_id, text, parse_mode="Markdown")
                except Exception:
                    log.exception("push to %s failed", chat_id)
        subscribers.add_seen([x["id"] for x in fresh])
        log.info("pushed %s site events to %s chats", len(fresh), len(chats))

    async def site_sync_loop(self) -> None:
        await self.sync_site_once(bootstrap=True)
        while True:
            await asyncio.sleep(SYNC_INTERVAL_SEC)
            try:
                await self.sync_site_once()
            except Exception:
                log.exception("site sync loop error")

    async def poll_loop(self) -> None:
        while True:
            try:
                updates = await self.call(
                    "getUpdates",
                    {
                        "offset": self.offset,
                        "timeout": 25,
                        "allowed_updates": ["message", "callback_query"],
                    },
                )
                for upd in updates:
                    self.offset = max(self.offset, int(upd["update_id"]) + 1)
                    try:
                        await self.handle_update(upd)
                    except Exception:
                        log.exception("update failed")
            except httpx.ReadTimeout:
                continue
            except Exception:
                log.exception("polling error")
                await asyncio.sleep(2)

    async def run(self) -> None:
        me = await self.call("getMe")
        log.info("Bot @%s online · mirroring site API", me.get("username"))
        try:
            await self.call("deleteWebhook", {"drop_pending_updates": True})
        except Exception:
            pass
        await asyncio.gather(self.poll_loop(), self.site_sync_loop())


async def main() -> None:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан в backend/.env")

    api = SctApi()
    try:
        health = await api.health()
        log.info("API ok: %s · base=%s", health.get("status"), api.base)
    except Exception as e:
        log.warning("API недоступен (%s) — бот всё равно стартует", e)

    bot = TgBot(token, api)
    try:
        await bot.run()
    finally:
        await bot.close()
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
