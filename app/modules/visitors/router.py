import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.common.pagination import PaginatedResponse
from app.common.schemas import MessageResponse
from app.core.dependencies import AdminOrSuperAdmin, AllStaff, DbSession, PaginationDep
from app.modules.visitors.schemas import VisitorCreate, VisitorResponse, VisitorUpdate
from app.modules.visitors.service import VisitorService

router = APIRouter(prefix="/visitors", tags=["Visitors"])


@router.post(
    "",
    response_model=VisitorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi tashrifchi qo'shish",
)
async def create_visitor(
    payload: VisitorCreate,
    current_user: AllStaff,
    db: DbSession,
) -> VisitorResponse:
    """Register a new visitor profile."""
    visitor = await VisitorService(db).create_visitor(payload, current_user)
    return VisitorResponse.model_validate(visitor)


@router.get(
    "",
    response_model=PaginatedResponse[VisitorResponse],
    status_code=status.HTTP_200_OK,
    summary="Tashrifchilar ro'yxati va qidiruv",
)
async def list_visitors(
    db: DbSession,
    pagination: PaginationDep,
    search: Annotated[
        str | None,
        Query(max_length=100, description="Ism yoki telefon raqami bo'yicha qidirish"),
    ] = None,
) -> PaginatedResponse[VisitorResponse]:
    """List active visitors with optional name/phone substring search."""
    return await VisitorService(db).list_visitors(pagination, search=search)


@router.get(
    "/{visitor_id}",
    response_model=VisitorResponse,
    status_code=status.HTTP_200_OK,
    summary="Tashrifchini ko'rish",
)
async def get_visitor(
    visitor_id: uuid.UUID,
    db: DbSession,
) -> VisitorResponse:
    """Retrieve a single active visitor profile by ID."""
    visitor = await VisitorService(db).get_visitor(visitor_id)
    return VisitorResponse.model_validate(visitor)


@router.patch(
    "/{visitor_id}",
    response_model=VisitorResponse,
    status_code=status.HTTP_200_OK,
    summary="Tashrifchi ma'lumotlarini tahrirlash",
)
async def update_visitor(
    visitor_id: uuid.UUID,
    payload: VisitorUpdate,
    current_user: AllStaff,
    db: DbSession,
) -> VisitorResponse:
    """Update an existing visitor's details."""
    visitor = await VisitorService(db).update_visitor(visitor_id, payload)
    return VisitorResponse.model_validate(visitor)


@router.delete(
    "/{visitor_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Tashrifchini o'chirish (Admin / Super Admin)",
)
async def delete_visitor(
    visitor_id: uuid.UUID,
    current_user: AdminOrSuperAdmin,
    db: DbSession,
) -> MessageResponse:
    """Soft-delete a visitor who is not currently inside the building."""
    await VisitorService(db).delete_visitor(visitor_id)
    return MessageResponse(message="Tashrifchi muvaffaqiyatli o'chirildi")
