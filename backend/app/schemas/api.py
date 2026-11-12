from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    status: str
    data_quality: str
    disclaimer: str


class RiskFactor(BaseModel):
    code: str
    label: str
    contribution_hours: float
    note: str = "Ассоциативный фактор, не доказанная причина задержки."


class LegOut(BaseModel):
    id: str
    sequence: int
    mode: str
    label: str = ""
    origin_name: str
    destination_name: str
    distance_km: float
    planned_departure: datetime
    planned_arrival: datetime
    predicted_departure: Optional[datetime] = None
    predicted_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    scheduled_service_id: Optional[str] = None
    status: str
    stage_status_label: str = ""
    data_quality: str


class EventOut(BaseModel):
    id: str
    event_type: str
    title: str = ""
    occurred_at: datetime
    available_at: datetime
    payload: dict[str, Any]
    source: str
    data_quality: str


class ShipmentSummary(BaseModel):
    id: str
    reference: str
    status: str
    risk_level: str
    route_from: str = ""
    route_to: str = ""
    route_label: str = ""
    current_stage: str = ""
    planned_eta: datetime
    predicted_eta: Optional[datetime]
    delay_hours: float
    missed_connection: bool
    cargo_description: str
    container_no: str = ""
    documents_ready: int = 0
    documents_total: int = 5
    documents_label: str = ""
    attention_title: Optional[str] = None
    attention_detail: Optional[str] = None
    data_quality: str


class ShipmentsList(BaseModel):
    items: list[ShipmentSummary]
    data_quality: str


class DocumentOut(BaseModel):
    id: str
    document_type: str
    status: str
    required: bool
    updated_at: datetime
    disclaimer: str
    data_quality: str


class DocumentsResponse(BaseModel):
    shipment_id: str
    completeness: float
    missing: list[str]
    documents: list[DocumentOut]
    disclaimer: str
    data_quality: str


class PredictionOut(BaseModel):
    id: str
    model_name: str
    as_of_ts: datetime
    predicted_eta: datetime
    delay_hours: float
    missed_connection: bool
    risk_factors: list[RiskFactor]
    mae_hours_holdout: Optional[float] = None
    notes: str
    data_quality: str


class ShipmentDetail(BaseModel):
    id: str
    reference: str
    cargo_description: str
    cargo_tonnes: float
    container_no: str = ""
    equipment: str = ""
    cargo_line: str = ""
    route_from: str = ""
    route_to: str = ""
    route_label: str = ""
    current_stage: str = ""
    current_location: str = ""
    status: str
    risk_level: str
    risk_headline: Optional[str] = None
    risk_detail: Optional[str] = None
    planned_eta: datetime
    predicted_eta: Optional[datetime]
    delay_hours: float
    missed_connection: bool
    selected_alternative_id: Optional[str]
    active_scenario: str = "storm"
    cost_rub: float = 0
    co2e_tonnes: float = 0
    documents_ready: int = 0
    documents_total: int = 5
    legs: list[LegOut]
    timeline: list[EventOut]
    documents: DocumentsResponse
    latest_prediction: Optional[PredictionOut]
    schedule_disclaimer: str = ""
    data_quality: str


class SimulateRequest(BaseModel):
    weather_severity_index: float = Field(ge=0.0, le=1.0, default=0.5)
    port_queue_hours: float = Field(ge=0.0, le=72.0, default=8.0)
    document_delay_hours: float = Field(ge=0.0, le=72.0, default=0.0)
    scenario: Optional[str] = None
    as_of: Optional[datetime] = None


class SimulateResponse(BaseModel):
    shipment_id: str
    missed_connection: bool
    missed_service_id: Optional[str]
    next_service_id: Optional[str]
    predicted_eta: datetime
    delay_hours: float
    risk_level: str
    risk_factors: list[RiskFactor]
    legs: list[LegOut]
    model_name: str
    mae_hours_holdout: Optional[float]
    active_scenario: str = "storm"
    data_quality: str


class AlternativeOut(BaseModel):
    id: str
    title: str
    subtitle: str = ""
    feasible: bool
    is_current: bool = False
    recommended: bool = False
    eta: Optional[datetime]
    eta_label: Optional[str] = None
    delay_hours: Optional[float] = None
    delay_label: Optional[str] = None
    total_hours: Optional[float]
    duration_label: Optional[str] = None
    cost_rub: Optional[float] = None
    cost_label: Optional[str] = None
    cost_delta_pct: Optional[int] = None
    cost_usd: Optional[float] = None
    transfers: Optional[int] = None
    co2e_tonnes: Optional[float] = None
    co2e_kg: Optional[float] = None
    co2e_label: Optional[str] = None
    co2e_delta_pct: Optional[int] = None
    constraints: Optional[str] = None
    availability: Optional[str] = None
    action_label: Optional[str] = None
    description: str
    assumptions: list[str]
    infeasible_reason: Optional[str] = None


class AlternativesResponse(BaseModel):
    shipment_id: str
    reference: str = ""
    route_label: str = ""
    insight: Optional[dict[str, str]] = None
    alternatives: list[AlternativeOut]
    infeasible_reason: Optional[str]
    footnote: str = ""
    co2_disclaimer: str
    data_quality: str
    planned_eta: Optional[datetime] = None


class SelectAlternativeRequest(BaseModel):
    alternative_id: str


class PredeclareRequest(BaseModel):
    shipment_id: str
    document_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class PredeclareResponse(BaseModel):
    document_id: str
    status: str
    disclaimer: str
    data_quality: str


class DocumentHistoryOut(BaseModel):
    document_id: str
    history: list[dict[str, Any]]
    disclaimer: str
    data_quality: str


class OverviewOut(BaseModel):
    title: str
    subtitle: str
    refreshed_at: datetime
    kpis: dict[str, int]
    attention: list[dict[str, Any]]
    shipments: list[ShipmentSummary]
    selected_map_reference: Optional[str] = "SCT-2048"
    data_quality: str
    disclaimer: str
