import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.pagination import PaginatedResponse, PaginationParams
from app.common.validators import clean_optional_text
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.users.models import User
from app.modules.visitors.models import Visitor
from app.modules.visitors.repository import VisitorRepository
from app.modules.visitors.schemas import VisitorCreate, VisitorResponse, VisitorUpdate
from app.modules.visits.repository import VisitRepository


class VisitorService:
    """Business logic for visitor CRUD and soft-delete integrity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.visitor_repo = VisitorRepository(session)
        self.visit_repo = VisitRepository(session)

    async def create_visitor(self, payload: VisitorCreate, actor: User) -> Visitor:
        """Create a new visitor profile ensuring active phone uniqueness."""
        if await self.visitor_repo.get_active_by_phone(payload.phone) is not None:
            raise ConflictError("Bu telefon raqami bilan tashrifchi allaqachon mavjud")

        visitor = Visitor(
            full_name=payload.full_name.strip(),
            phone=payload.phone,
            document_number=clean_optional_text(payload.document_number),
            organization=clean_optional_text(payload.organization),
            notes=clean_optional_text(payload.notes),
            created_by=actor.id,
        )
        try:
            await self.visitor_repo.add(visitor)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Bu telefon raqami bilan tashrifchi allaqachon mavjud") from exc

        await self.session.refresh(visitor)
        return visitor

    async def get_visitor(self, visitor_id: uuid.UUID) -> Visitor:
        """Retrieve an active visitor by ID or raise NotFoundError."""
        visitor = await self.visitor_repo.get_active_by_id(visitor_id)
        if visitor is None:
            raise NotFoundError("Tashrifchi topilmadi")
        return visitor

    async def list_visitors(
        self,
        pagination: PaginationParams,
        *,
        search: str | None = None,
    ) -> PaginatedResponse[VisitorResponse]:
        """List active visitors with pagination and optional name/phone search."""
        items, total = await self.visitor_repo.list_active(
            offset=pagination.offset,
            limit=pagination.size,
            search=search,
        )
        return PaginatedResponse.create(
            items=[VisitorResponse.model_validate(item) for item in items],
            total=total,
            page=pagination.page,
            size=pagination.size,
        )

    async def update_visitor(
        self,
        visitor_id: uuid.UUID,
        payload: VisitorUpdate,
    ) -> Visitor:
        """Update an active visitor's details while preserving unique phone numbers."""
        visitor = await self.get_visitor(visitor_id)
        fields = payload.model_fields_set

        if "full_name" in fields:
            if payload.full_name is None:
                raise BadRequestError("Tashrifchi ismi bo'sh bo'lishi mumkin emas")
            visitor.full_name = payload.full_name.strip()

        if "phone" in fields:
            if payload.phone is None:
                raise BadRequestError("Telefon raqami bo'sh bo'lishi mumkin emas")
            if payload.phone != visitor.phone:
                existing = await self.visitor_repo.get_active_by_phone(payload.phone)
                if existing is not None and existing.id != visitor.id:
                    raise ConflictError("Bu telefon raqami boshqa tashrifchiga biriktirilgan")
                visitor.phone = payload.phone

        if "document_number" in fields:
            visitor.document_number = clean_optional_text(payload.document_number)
        if "organization" in fields:
            visitor.organization = clean_optional_text(payload.organization)
        if "notes" in fields:
            visitor.notes = clean_optional_text(payload.notes)

        try:
            await self.visitor_repo.save(visitor)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Bu telefon raqami boshqa tashrifchiga biriktirilgan") from exc

        await self.session.refresh(visitor)
        return visitor

    async def delete_visitor(self, visitor_id: uuid.UUID) -> None:
        """Soft-delete a visitor if they do not currently have an open visit."""
        visitor = await self.get_visitor(visitor_id)
        active_visit = await self.visit_repo.get_active_by_visitor_id(visitor.id)
        if active_visit is not None:
            raise ConflictError(
                "Hozir binoda bo'lgan tashrifchini o'chirib bo'lmaydi. Avval chiqishni qayd eting"
            )

        visitor.deleted_at = datetime.now(UTC)
        await self.visitor_repo.save(visitor)
        await self.session.commit()
