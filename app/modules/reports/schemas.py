import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.common.enums import VisitStatus


class ReportRowResponse(BaseModel):
    """Single visit row included in reports and exports."""

    visit_id: uuid.UUID
    visitor_name: str
    visitor_phone: str
    organization: str | None
    purpose: str | None
    host_name: str | None
    badge_number: str | None
    checked_in_at: datetime
    checked_out_at: datetime | None
    duration_minutes: int | None
    status: VisitStatus
    checked_in_by_name: str | None
    checked_out_by_name: str | None


class ReportSummaryResponse(BaseModel):
    """Aggregated visit report for a selected date range."""

    start_date: date
    end_date: date
    total_visits: int
    completed_visits: int
    currently_inside: int
    items: list[ReportRowResponse]
