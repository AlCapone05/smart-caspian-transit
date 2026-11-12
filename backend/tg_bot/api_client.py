"""HTTP client for SCT FastAPI."""

from __future__ import annotations

import os
from typing import Any

import httpx

API_BASE = os.getenv("SCT_API_BASE", "http://127.0.0.1:8002/api/v1").rstrip("/")
API_KEY = os.getenv("API_KEY", "demo-key")


class SctApi:
    def __init__(self, base: str | None = None, api_key: str | None = None) -> None:
        self.base = (base or API_BASE).rstrip("/")
        self.api_key = api_key or API_KEY
        self._client = httpx.AsyncClient(
            base_url=self.base,
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, **params: Any) -> dict:
        r = await self._client.get(path, params=params or None)
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, body: dict | None = None) -> dict:
        r = await self._client.post(path, json=body or {})
        r.raise_for_status()
        return r.json()

    async def health(self) -> dict:
        return await self._get("/health")

    async def overview(self) -> dict:
        return await self._get("/overview")

    async def shipment(self, ref_or_id: str) -> dict:
        r = await self._client.get(f"/shipments/{ref_or_id}")
        if r.status_code == 404:
            raise ValueError("Груз не найден")
        r.raise_for_status()
        return r.json()

    async def list_shipments(self) -> dict:
        return await self._get("/shipments")

    async def notifications(self) -> dict:
        return await self._get("/notifications")

    async def tracking(self) -> dict:
        return await self._get("/tracking")

    async def tracking_alerts(self) -> dict:
        return await self._get("/tracking/alerts")

    async def alternatives(self, shipment_id: str) -> dict:
        return await self._get(f"/shipments/{shipment_id}/alternatives")

    async def select_alternative(self, shipment_id: str, alternative_id: str) -> dict:
        return await self._post(
            f"/shipments/{shipment_id}/select-alternative",
            {"alternative_id": alternative_id},
        )

    async def select_vessel_route(self, vessel_id: str, alternative_id: str) -> dict:
        return await self._post(
            f"/tracking/vessels/{vessel_id}/select-route",
            {"alternative_id": alternative_id},
        )

    async def assistant(self, message: str, history: list[dict] | None = None) -> dict:
        return await self._post("/assistant/chat", {"message": message, "history": history or []})
