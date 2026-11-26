import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums import VisitStatus
from app.common.validators import escape_like
from app.modules.visitors.models import Visitor
from app.modules.visits.models import Visit


class VisitRepository:
    """Data access layer for Visit check-in/check-out records and history."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, visit_id: uuid.UUID) -> Visit | None:
        """Fetch a visit by UUID with its associated visitor loaded."""
        stmt = (
            select(Visit)
            .options(selectinload(Visit.visitor))
            .where(Visit.id == visit_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_visitor_id(self, visitor_id: uuid.UUID) -> Visit | None:
        """Fetch the currently open (not checked out) visit for a visitor, if any."""
        stmt = (
            select(Visit)
            .options(selectinload(Visit.visitor))
            .where(
                Visit.visitor_id == visitor_id,
                Visit.checked_out_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_visits(
        self,
        *,
        offset: int,
        limit: int,
        visitor_id: uuid.UUID | None = None,
        status: VisitStatus | None = None,
        search: str | None = None,
        checked_in_from: datetime | None = None,
        checked_in_to_exclusive: datetime | None = None,
    ) -> tuple[list[Visit], int]:
        """Return paginated visits matching optional visitor, status, search, and date filters."""
        conditions = []
        if visitor_id is not None:
            conditions.append(Visit.visitor_id == visitor_id)
        if status == VisitStatus.INSIDE:
            conditions.append(Visit.checked_out_at.is_(None))
        elif status == VisitStatus.COMPLETED:
            conditions.append(Visit.checked_out_at.is_not(None))
        if checked_in_from is not None:
            conditions.append(Visit.checked_in_at >= checked_in_from)
        if checked_in_to_exclusive is not None:
            conditions.append(Visit.checked_in_at < checked_in_to_exclusive)

        has_search = bool(search and search.strip())
        count_stmt = select(func.count(Visit.id))
        items_stmt = select(Visit).options(selectinload(Visit.visitor))

        if has_search and search is not None:
            pattern = f"%{escape_like(search.strip())}%"
            search_filter = or_(
                Visitor.full_name.ilike(pattern, escape="\\"),
                Visitor.phone.ilike(pattern, escape="\\"),
            )
            count_stmt = count_stmt.join(Visit.visitor).where(search_filter)
            items_stmt = items_stmt.join(Visit.visitor).where(search_filter)

        if conditions:
            count_stmt = count_stmt.where(*conditions)
            items_stmt = items_stmt.where(*conditions)

        total = int((await self.session.execute(count_stmt)).scalar_one())

        items_stmt = (
            items_stmt.order_by(Visit.checked_in_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.session.execute(items_stmt)).scalars().all())
        return items, total

    async def add(self, visit: Visit) -> Visit:
        """Stage a new Visit in the session and flush."""
        self.session.add(visit)
        await self.session.flush()
        return visit

    async def save(self, visit: Visit) -> Visit:
        """Flush updates for an existing Visit."""
        await self.session.flush()
        return visit
