from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.visitors.models import Visitor
from app.modules.visits.models import Visit


@dataclass(frozen=True, slots=True)
class OverviewCounts:
    """Raw aggregated counts from PostgreSQL for dashboard statistics."""

    today_visits: int
    weekly_visits: int
    monthly_visits: int
    total_visitors: int
    currently_inside: int


class StatisticsRepository:
    """Read-only aggregation queries for visitor and visit statistics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_overview_counts(
        self,
        *,
        today_start: datetime,
        week_start: datetime,
        month_start: datetime,
        tomorrow_start: datetime,
    ) -> OverviewCounts:
        """Compute period visit counts, live occupancy, and active visitor total."""
        visits_stmt = select(
            func.count(Visit.id)
            .filter(
                Visit.checked_in_at >= today_start,
                Visit.checked_in_at < tomorrow_start,
            )
            .label("today_visits"),
            func.count(Visit.id)
            .filter(
                Visit.checked_in_at >= week_start,
                Visit.checked_in_at < tomorrow_start,
            )
            .label("weekly_visits"),
            func.count(Visit.id)
            .filter(
                Visit.checked_in_at >= month_start,
                Visit.checked_in_at < tomorrow_start,
            )
            .label("monthly_visits"),
            func.count(Visit.id)
            .filter(Visit.checked_out_at.is_(None))
            .label("currently_inside"),
        )
        visits_row = (await self.session.execute(visits_stmt)).one()

        visitors_stmt = select(func.count(Visitor.id)).where(Visitor.deleted_at.is_(None))
        total_visitors = int((await self.session.execute(visitors_stmt)).scalar_one())

        return OverviewCounts(
            today_visits=int(visits_row.today_visits or 0),
            weekly_visits=int(visits_row.weekly_visits or 0),
            monthly_visits=int(visits_row.monthly_visits or 0),
            total_visitors=total_visitors,
            currently_inside=int(visits_row.currently_inside or 0),
        )

    async def get_daily_counts(
        self,
        *,
        start_utc: datetime,
        end_exclusive_utc: datetime,
        timezone_name: str,
    ) -> dict[date, int]:
        """Return visit counts grouped by local calendar date in the UTC range."""
        local_day = func.date(func.timezone(timezone_name, Visit.checked_in_at))
        stmt = (
            select(local_day.label("visit_date"), func.count(Visit.id).label("visits_count"))
            .where(
                Visit.checked_in_at >= start_utc,
                Visit.checked_in_at < end_exclusive_utc,
            )
            .group_by(local_day)
            .order_by(local_day.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        return {row.visit_date: int(row.visits_count) for row in rows}
