import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.validators import escape_like
from app.modules.visitors.models import Visitor


class VisitorRepository:
    """Data access layer for active (non-deleted) Visitor entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_by_id(self, visitor_id: uuid.UUID) -> Visitor | None:
        """Fetch an active visitor by UUID."""
        stmt = select(Visitor).where(
            Visitor.id == visitor_id,
            Visitor.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_phone(self, phone: str) -> Visitor | None:
        """Fetch an active visitor by normalized phone number."""
        stmt = select(Visitor).where(
            Visitor.phone == phone,
            Visitor.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(
        self,
        *,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> tuple[list[Visitor], int]:
        """Return paginated active visitors with optional name/phone substring search."""
        conditions = [Visitor.deleted_at.is_(None)]
        if search and search.strip():
            pattern = f"%{escape_like(search.strip())}%"
            conditions.append(
                or_(
                    Visitor.full_name.ilike(pattern, escape="\\"),
                    Visitor.phone.ilike(pattern, escape="\\"),
                )
            )

        count_stmt = select(func.count(Visitor.id)).where(*conditions)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        items_stmt = (
            select(Visitor)
            .where(*conditions)
            .order_by(Visitor.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.session.execute(items_stmt)).scalars().all())
        return items, total

    async def add(self, visitor: Visitor) -> Visitor:
        """Stage a new Visitor in the session and flush."""
        self.session.add(visitor)
        await self.session.flush()
        return visitor

    async def save(self, visitor: Visitor) -> Visitor:
        """Flush updates for an existing Visitor."""
        await self.session.flush()
        return visitor
