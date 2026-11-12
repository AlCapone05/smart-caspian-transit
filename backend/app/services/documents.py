from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Document, DocumentStatusHistory, Shipment

DISCLAIMER = "Статус комплекта документов. Не заменяет решение таможенного органа."
PACKAGE_TYPES = [
    "commercial_invoice",
    "packing_list",
    "bill_of_lading_draft",
    "certificate_of_origin",
    "insurance_policy",
]
# legacy alias
REQUIRED_TYPES = PACKAGE_TYPES

DOC_TITLES = {
    "commercial_invoice": "Коммерческий инвойс",
    "packing_list": "Упаковочный лист",
    "bill_of_lading_draft": "Транспортная накладная",
    "certificate_of_origin": "Сертификат происхождения",
    "hs_code_declaration": "Декларация ТН ВЭД",
    "insurance_policy": "Страховой полис",
}


def documents_payload(shipment: Shipment) -> dict:
    docs = shipment.documents
    required = [d for d in docs if d.required]
    complete_statuses = {"accepted_for_review", "submitted", "complete"}
    ok = sum(1 for d in required if d.status in complete_statuses)
    completeness = round(ok / len(required), 2) if required else 1.0
    missing = [d.document_type for d in required if d.status not in complete_statuses]
    return {
        "shipment_id": shipment.id,
        "completeness": completeness,
        "missing": missing,
        "documents": [
            {
                "id": d.id,
                "document_type": d.document_type,
                "status": d.status,
                "required": d.required,
                "updated_at": d.updated_at,
                "disclaimer": d.disclaimer,
                "data_quality": d.data_quality,
            }
            for d in docs
        ],
        "disclaimer": DISCLAIMER,
        "data_quality": "synthetic_demo",
    }


async def _resolve_shipment(session: AsyncSession, shipment_id: str) -> Shipment:
    result = await session.execute(
        select(Shipment)
        .where((Shipment.id == shipment_id) | (Shipment.reference == shipment_id))
        .options(selectinload(Shipment.documents))
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise ValueError("Shipment not found")
    return shipment


async def ensure_package_docs(session: AsyncSession, shipment: Shipment) -> None:
    """Guarantee the MVP 5-doc package exists for a shipment."""
    existing = {d.document_type: d for d in shipment.documents}
    now = datetime.now(timezone.utc)
    for dtype in PACKAGE_TYPES:
        if dtype in existing:
            continue
        doc = Document(
            id=f"doc_{uuid.uuid4().hex[:10]}",
            shipment_id=shipment.id,
            document_type=dtype,
            status="missing",
            required=True,
            payload={},
            updated_at=now,
            disclaimer=DISCLAIMER,
            data_quality="synthetic_demo",
        )
        session.add(doc)
        shipment.documents.append(doc)


async def add_or_update_document(
    session: AsyncSession,
    *,
    shipment_id: str,
    document_type: str | None = None,
    document_id: str | None = None,
    file_name: str | None = None,
    hs_code: str | None = None,
    mark_complete: bool = False,
    payload: dict | None = None,
) -> Document:
    shipment = await _resolve_shipment(session, shipment_id)
    await ensure_package_docs(session, shipment)
    await session.flush()

    now = datetime.now(timezone.utc)
    doc: Document | None = None
    if document_id:
        doc = next((d for d in shipment.documents if d.id == document_id), None)
    elif document_type:
        doc = next((d for d in shipment.documents if d.document_type == document_type), None)
        if not doc:
            doc = Document(
                id=f"doc_{uuid.uuid4().hex[:10]}",
                shipment_id=shipment.id,
                document_type=document_type,
                status="missing",
                required=document_type in PACKAGE_TYPES,
                payload={},
                updated_at=now,
                disclaimer=DISCLAIMER,
                data_quality="synthetic_demo",
            )
            session.add(doc)
            await session.flush()

    if not doc:
        raise ValueError("document_id or document_type required")

    body = dict(doc.payload or {})
    if payload:
        body.update(payload)
    notes: list[str] = []

    if hs_code is not None:
        code = hs_code.strip()
        if not (code.isdigit() and len(code) == 10):
            raise ValueError("HS code must be 10 digits")
        body["hs_code"] = code
        notes.append(f"Указан код ТН ВЭД: {code}")

    if file_name:
        body["file_name"] = file_name
        body["file_size_mb"] = body.get("file_size_mb", 1.2)
        notes.append(f"Добавлен файл: {file_name}")

    if mark_complete or (hs_code and doc.document_type in {"certificate_of_origin", "hs_code_declaration"}):
        doc.status = "complete"
    elif file_name or body.get("file_name"):
        doc.status = "submitted" if doc.status == "missing" else (
            "complete" if mark_complete else "submitted"
        )
    elif hs_code:
        doc.status = "complete"
    else:
        raise ValueError("Nothing to update: provide file_name, hs_code, or mark_complete")

    if mark_complete:
        doc.status = "complete"
        notes.append("Отмечен как проверенный (демо)")

    doc.payload = body
    doc.updated_at = now
    session.add(
        DocumentStatusHistory(
            id=f"dsh_{uuid.uuid4().hex[:10]}",
            document_id=doc.id,
            status=doc.status,
            note="; ".join(notes) or "Документ обновлён",
            changed_at=now,
            actor="api:documents",
            data_quality="synthetic_demo",
        )
    )
    await session.commit()
    await session.refresh(doc)
    return doc


async def predeclare(
    session: AsyncSession,
    *,
    shipment_id: str,
    document_type: str,
    payload: dict,
) -> Document:
    return await add_or_update_document(
        session,
        shipment_id=shipment_id,
        document_type=document_type,
        file_name=(payload or {}).get("file_name") or f"{document_type}_demo.pdf",
        hs_code=(payload or {}).get("hs_code"),
        payload=payload or {"demo": True},
        mark_complete=False,
    )


async def document_history(session: AsyncSession, document_id: str) -> dict:
    result = await session.execute(
        select(Document).where(Document.id == document_id).options(selectinload(Document.history))
    )
    doc = result.scalar_one()
    history = sorted(doc.history, key=lambda h: h.changed_at)
    return {
        "document_id": doc.id,
        "history": [
            {
                "id": h.id,
                "status": h.status,
                "note": h.note,
                "changed_at": h.changed_at.isoformat(),
                "actor": h.actor,
                "data_quality": h.data_quality,
            }
            for h in history
        ],
        "disclaimer": DISCLAIMER,
        "data_quality": "synthetic_demo",
    }
