from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Port(Base):
    __tablename__ = "ports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    country: Mapped[str] = mapped_column(String(8))
    timezone: Mapped[str] = mapped_column(String(64))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    handling_norm_hours: Mapped[float] = mapped_column(Float, default=12.0)
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic_demo")


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    reference: Mapped[str] = mapped_column(String(64), unique=True)
    cargo_description: Mapped[str] = mapped_column(String(256))
    cargo_tonnes: Mapped[float] = mapped_column(Float, default=20.0)
    container_no: Mapped[str] = mapped_column(String(64), default="")
    equipment: Mapped[str] = mapped_column(String(64), default="1 × 40′ HC")
    route_from: Mapped[str] = mapped_column(String(128), default="")
    route_to: Mapped[str] = mapped_column(String(128), default="")
    current_stage: Mapped[str] = mapped_column(String(128), default="")
    current_location: Mapped[str] = mapped_column(String(256), default="")
    attention_title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    attention_detail: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    risk_headline: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    risk_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cost_rub: Mapped[float] = mapped_column(Float, default=180000.0)
    co2e_tonnes: Mapped[float] = mapped_column(Float, default=1.84)
    status: Mapped[str] = mapped_column(String(32), default="planned")
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    planned_eta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    predicted_eta: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delay_hours: Mapped[float] = mapped_column(Float, default=0.0)
    missed_connection: Mapped[bool] = mapped_column(Boolean, default=False)
    selected_alternative_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    active_scenario: Mapped[str] = mapped_column(String(32), default="storm")
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic_demo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    legs: Mapped[list["TransportLeg"]] = relationship(
        back_populates="shipment", order_by="TransportLeg.sequence"
    )
    events: Mapped[list["Event"]] = relationship(back_populates="shipment")
    documents: Mapped[list["Document"]] = relationship(back_populates="shipment")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="shipment")


class TransportLeg(Base):
    __tablename__ = "transport_legs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"))
    sequence: Mapped[int] = mapped_column(Integer)
    mode: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(64), default="")
    origin_name: Mapped[str] = mapped_column(String(128))
    destination_name: Mapped[str] = mapped_column(String(128))
    origin_port_id: Mapped[Optional[str]] = mapped_column(ForeignKey("ports.id"), nullable=True)
    destination_port_id: Mapped[Optional[str]] = mapped_column(ForeignKey("ports.id"), nullable=True)
    distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    planned_departure: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    planned_arrival: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_departure: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    predicted_departure: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    predicted_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_service_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    planned_scheduled_service_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="planned")
    stage_status_label: Mapped[str] = mapped_column(String(64), default="")
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic_demo")

    shipment: Mapped["Shipment"] = relationship(back_populates="legs")


class ScheduledService(Base):
    __tablename__ = "scheduled_services"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    mode: Mapped[str] = mapped_column(String(32))
    origin_port_id: Mapped[str] = mapped_column(ForeignKey("ports.id"))
    destination_port_id: Mapped[str] = mapped_column(ForeignKey("ports.id"))
    departure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    arrival_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capacity_teu: Mapped[int] = mapped_column(Integer, default=100)
    cutoff_hours: Mapped[float] = mapped_column(Float, default=6.0)
    compatible_cargo: Mapped[str] = mapped_column(String(64), default="container")
    is_demo_schedule: Mapped[bool] = mapped_column(Boolean, default=True)
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic_demo")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"))
    leg_id: Mapped[Optional[str]] = mapped_column(ForeignKey("transport_legs.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(256), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(32), default="simulator")
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic_demo")

    shipment: Mapped["Shipment"] = relationship(back_populates="events")


class WeatherForecast(Base):
    __tablename__ = "weather_forecasts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    port_id: Mapped[str] = mapped_column(ForeignKey("ports.id"))
    forecast_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    severity_index: Mapped[float] = mapped_column(Float, default=0.0)
    wind_ms: Mapped[float] = mapped_column(Float, default=0.0)
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic_demo")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"))
    document_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), default="missing")
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    disclaimer: Mapped[str] = mapped_column(
        Text,
        default="Тестовый статус. Не является таможенным разрешением.",
    )
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic_demo")

    shipment: Mapped["Shipment"] = relationship(back_populates="documents")
    history: Mapped[list["DocumentStatusHistory"]] = relationship(back_populates="document")


class DocumentStatusHistory(Base):
    __tablename__ = "document_status_history"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    status: Mapped[str] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(Text, default="")
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[str] = mapped_column(String(64), default="api")
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic_demo")

    document: Mapped["Document"] = relationship(back_populates="history")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"))
    model_name: Mapped[str] = mapped_column(String(64))
    as_of_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    predicted_eta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delay_hours: Mapped[float] = mapped_column(Float)
    missed_connection: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_factors: Mapped[list] = mapped_column(JSON, default=list)
    mae_hours_holdout: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic_demo")

    shipment: Mapped["Shipment"] = relationship(back_populates="predictions")


class Vessel(Base):
    """Demo AIS/GPS vessel on Caspian routes."""

    __tablename__ = "vessels"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    mmsi: Mapped[str] = mapped_column(String(32), default="")
    shipment_id: Mapped[Optional[str]] = mapped_column(ForeignKey("shipments.id"), nullable=True)
    route_label: Mapped[str] = mapped_column(String(128), default="")
    origin_port_id: Mapped[str] = mapped_column(String(64), default="")
    destination_port_id: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="underway")
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    heading_deg: Mapped[float] = mapped_column(Float, default=0.0)
    speed_knots: Mapped[float] = mapped_column(Float, default=10.0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1 along route
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic_demo")


class WeatherAlert(Base):
    """Predictive weather / storm alert for dispatcher."""

    __tablename__ = "weather_alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))  # storm | wind | fog | wave
    severity: Mapped[str] = mapped_column(String(16), default="medium")  # low|medium|high
    title: Mapped[str] = mapped_column(String(256))
    detail: Mapped[str] = mapped_column(Text, default="")
    port_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lat: Mapped[float] = mapped_column(Float, default=0.0)
    lon: Mapped[float] = mapped_column(Float, default=0.0)
    wind_ms: Mapped[float] = mapped_column(Float, default=0.0)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    predicted: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    affected_vessel_ids: Mapped[list] = mapped_column(JSON, default=list)
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic_demo")
