from datetime import date, datetime

from pydantic import BaseModel


class OverviewStatsResponse(BaseModel):
    """Real-time visitor and visit summary statistics."""

    today_visits: int
    weekly_visits: int
    monthly_visits: int
    total_visitors: int
    currently_inside: int
    timezone: str
    generated_at: datetime


class DailyVisitStatResponse(BaseModel):
    """Visit count for a single local calendar date."""

    date: date
    visits_count: int
