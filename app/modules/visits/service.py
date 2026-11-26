import uuid
from datetime import UTC, date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import local_day_end_exclusive_utc, local_day_start_utc
from app.common.enums import VisitStatus
from app.common.pagination import PaginatedResponse, PaginationParams
from app.common.validators import clean_optional_text
from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.users.models import User
from app.modules.visitors.repository import VisitorRepository
from app.modules.visits.models import Visit
from app.modules.visits.repository import VisitRepository
from app.modules.visits.schemas import CheckInRequest, CheckOutRequest, VisitResponse


class VisitService:
    """Business logic for visitor check-in, check-out, active occupancy, and history."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.visit_repo = VisitRepository(session)
        self.visitor_repo = VisitorRepository(session)

    async def _close_visit(
        self,
        visit: Visit,
        actor: User,
        payload: CheckOutRequest | None,
    ) -> Visit:
        """Shared check-out transition for an open visit record."""
        if visit.checked_out_at is not None:
            raise ConflictError("Ushbu tashrif bo'yicha chiqish allaqachon qayd etilgan")

        visit.checked_out_at = datetime.now(UTC)
        visit.checked_out_by = actor.id

        checkout_note = clean_optional_text(payload.notes if payload else None)
        if checkout_note:
            if visit.notes:
                visit.notes = f"{visit.notes}\n[Chiqish]: {checkout_note}"
            else:
                visit.notes = checkout_note

        await self.visit_repo.save(visit)
        await self.session.commit()
        reloaded = await self.visit_repo.get_by_id(visit.id)
        if reloaded is None:
            raise NotFoundError("Tashrif yozuvi topilmadi")
        return reloaded

    async def check_in(self, payload: CheckInRequest, actor: User) -> Visit:
        """Register a visitor entering the building if they have no open visit."""
        visitor = await self.visitor_repo.get_active_by_id(payload.visitor_id)
        if visitor is None:
            raise NotFoundError("Tashrifchi topilmadi")

        if await self.visit_repo.get_active_by_visitor_id(visitor.id) is not None:
            raise ConflictError(
                "Tashrifchi hozirda binoda. Qayta kirishdan oldin chiqishni qayd eting"
            )

        visit = Visit(
            visitor_id=visitor.id,
            checked_in_by=actor.id,
            purpose=clean_optional_text(payload.purpose),
            host_name=clean_optional_text(payload.host_name),
            badge_number=clean_optional_text(payload.badge_number),
            notes=clean_optional_text(payload.notes),
            checked_in_at=datetime.now(UTC),
        )
        try:
            await self.visit_repo.add(visit)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "Tashrifchi hozirda binoda. Qayta kirishdan oldin chiqishni qayd eting"
            ) from exc

        reloaded = await self.visit_repo.get_by_id(visit.id)
        if reloaded is None:
            raise NotFoundError("Tashrif yozuvi topilmadi")
        return reloaded

    async def check_out(
        self,
        visit_id: uuid.UUID,
        actor: User,
        payload: CheckOutRequest | None = None,
    ) -> Visit:
        """Check out a visitor by visit ID."""
        visit = await self.visit_repo.get_by_id(visit_id)
        if visit is None:
            raise NotFoundError("Tashrif yozuvi topilmadi")
        return await self._close_visit(visit, actor, payload)

    async def check_out_by_visitor(
        self,
        visitor_id: uuid.UUID,
        actor: User,
        payload: CheckOutRequest | None = None,
    ) -> Visit:
        """Check out a visitor's currently open visit by visitor ID."""
        visit = await self.visit_repo.get_active_by_visitor_id(visitor_id)
        if visit is None:
            raise NotFoundError("Ushbu tashrifchining binodagi ochiq tashrifi topilmadi")
        return await self._close_visit(visit, actor, payload)

    async def get_visit(self, visit_id: uuid.UUID) -> Visit:
        """Retrieve a single visit record by ID."""
        visit = await self.visit_repo.get_by_id(visit_id)
        if visit is None:
            raise NotFoundError("Tashrif yozuvi topilmadi")
        return visit

    async def list_active_visits(
        self,
        pagination: PaginationParams,
        *,
        search: str | None = None,
    ) -> PaginatedResponse[VisitResponse]:
        """List visitors who are currently inside the building."""
        return await self.list_visits(
            pagination,
            status=VisitStatus.INSIDE,
            search=search,
        )

    async def list_visits(
        self,
        pagination: PaginationParams,
        *,
        visitor_id: uuid.UUID | None = None,
        status: VisitStatus | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> PaginatedResponse[VisitResponse]:
        """List visit history with optional filters and pagination."""
        if date_from is not None and date_to is not None and date_from > date_to:
            raise BadRequestError("Boshlanish sanasi tugash sanasidan katta bo'lishi mumkin emas")

        tz = get_settings().tz
        checked_in_from = local_day_start_utc(date_from, tz) if date_from is not None else None
        checked_in_to_exclusive = (
            local_day_end_exclusive_utc(date_to, tz) if date_to is not None else None
        )

        items, total = await self.visit_repo.list_visits(
            offset=pagination.offset,
            limit=pagination.size,
            visitor_id=visitor_id,
            status=status,
            search=search,
            checked_in_from=checked_in_from,
            checked_in_to_exclusive=checked_in_to_exclusive,
        )
        return PaginatedResponse.create(
            items=[VisitResponse.model_validate(item) for item in items],
            total=total,
            page=pagination.page,
            size=pagination.size,
        )
