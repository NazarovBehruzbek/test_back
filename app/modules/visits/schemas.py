import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import VisitStatus


class CheckInRequest(BaseModel):
    """Payload for checking a visitor into the building."""

    visitor_id: uuid.UUID
    purpose: str | None = Field(default=None, max_length=255)
    host_name: str | None = Field(default=None, max_length=150)
    badge_number: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=1000)


class CheckOutRequest(BaseModel):
    """Optional remarks payload when checking a visitor out."""

    notes: str | None = Field(default=None, max_length=1000)


class VisitVisitorSummary(BaseModel):
    """Embedded visitor details returned with a visit record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    phone: str
    organization: str | None


class VisitResponse(BaseModel):
    """Visit record response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    visitor_id: uuid.UUID
    visitor: VisitVisitorSummary
    purpose: str | None
    host_name: str | None
    badge_number: str | None
    checked_in_at: datetime
    checked_out_at: datetime | None
    status: VisitStatus
    checked_in_by: uuid.UUID | None
    checked_out_by: uuid.UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
