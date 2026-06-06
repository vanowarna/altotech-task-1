"""Shared Pydantic models — request/response and domain DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Reading(BaseModel):
    """A single sensor reading as pushed by the edge simulator.

    Note: `brick_class` is intentionally absent — it is resolved from the graph
    at ingestion, never carried on the wire.
    """

    device_id: str
    datapoint: str
    value: float | str
    timestamp: int = Field(..., description="Unix epoch seconds")


class BatchReadings(BaseModel):
    readings: list[Reading]


class ResolvedReading(BaseModel):
    """A reading after Brick resolution, ready to persist."""

    device_id: str
    datapoint: str
    value_num: Optional[float] = None
    value_text: Optional[str] = None
    timestamp: int
    brick_class: str
    property_id: str
    location: str


class IngestResult(BaseModel):
    accepted: int
    rejected: int
    errors: list[str] = []


class PropertyIn(BaseModel):
    id: str
    name: str
    timezone: str = "UTC"
    config: dict[str, Any] = {}


class DeviceIn(BaseModel):
    id: str
    datapoint: str
    location_id: str
    property_id: str


class DeviceOut(BaseModel):
    id: str
    datapoint: str
    brick_class: str
    unit: Optional[str] = None
    location: Optional[str] = None
    floor: Optional[int] = None
    property_id: Optional[str] = None


class ReadingOut(BaseModel):
    time: datetime
    device_id: str
    datapoint: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    brick_class: Optional[str] = None


class RuleIn(BaseModel):
    id: Optional[str] = None
    name: str
    brick_class_target: str
    condition_type: str
    params: dict[str, Any] = {}
    severity: str = "warning"
    enabled: bool = True
    property_overrides: dict[str, Any] = {}


class RuleOut(BaseModel):
    id: str
    name: str
    brick_class_target: str
    condition_type: str
    params: dict[str, Any] = {}
    severity: str
    enabled: bool
    property_overrides: dict[str, Any] = {}


class FaultOut(BaseModel):
    id: str
    severity: str
    status: str
    detected_at: Optional[int] = None
    resolved_at: Optional[int] = None
    device_id: Optional[str] = None
    property_id: Optional[str] = None
    location: Optional[str] = None
    rule: Optional[str] = None
    brick_class: Optional[str] = None
    context: Optional[dict[str, Any]] = None
    notes: list[str] = []


class NoteIn(BaseModel):
    note: str
