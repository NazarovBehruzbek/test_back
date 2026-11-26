from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums import VisitStatus
from app.modules.visits.models import Visit


class ReportsRepository:
    """Read-only queries for generating date-range visit reports."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_visits_for_report(
        self,
        *,
        start_utc: datetime,
        end_exclusive_utc: datetime,
        status: VisitStatus | None = None,
    ) -> list[Visit]:
        """Fetch visits within [start_utc, end_exclusive_utc) with related entities loaded."""
        stmt = (
            select(Visit)
            .options(
                selectinload(Visit.visitor),
                selectinload(Visit.check_in_operator),
                selectinload(Visit.check_out_operator),
            )
            .where(
                Visit.checked_in_at >= start_utc,
                Visit.checked_in_at < end_exclusive_utc,
            )
        )
        if status == VisitStatus.INSIDE:
            stmt = stmt.where(Visit.checked_out_at.is_(None))
        elif status == VisitStatus.COMPLETED:
            stmt = stmt.where(Visit.checked_out_at.is_not(None))

        stmt = stmt.order_by(Visit.checked_in_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())
