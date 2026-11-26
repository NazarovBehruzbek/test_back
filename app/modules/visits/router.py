import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Query, status

from app.common.enums import VisitStatus
from app.common.pagination import PaginatedResponse
from app.core.dependencies import AllStaff, DbSession, PaginationDep
from app.modules.visits.schemas import CheckInRequest, CheckOutRequest, VisitResponse
from app.modules.visits.service import VisitService

router = APIRouter(prefix="/visits", tags=["Visits"])


@router.post(
    "/check-in",
    response_model=VisitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tashrifchi kirishini qayd etish (Check-in)",
)
async def check_in(
    payload: CheckInRequest,
    current_user: AllStaff,
    db: DbSession,
) -> VisitResponse:
    """Record a visitor's entry into the building."""
    visit = await VisitService(db).check_in(payload, current_user)
    return VisitResponse.model_validate(visit)


@router.post(
    "/{visit_id}/check-out",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
    summary="Tashrif ID bo'yicha chiqishni qayd etish (Check-out)",
)
async def check_out(
    visit_id: uuid.UUID,
    current_user: AllStaff,
    db: DbSession,
    payload: Annotated[CheckOutRequest | None, Body()] = None,
) -> VisitResponse:
    """Record a visitor's exit using the visit ID."""
    visit = await VisitService(db).check_out(visit_id, current_user, payload)
    return VisitResponse.model_validate(visit)


@router.post(
    "/visitors/{visitor_id}/check-out",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
    summary="Tashrifchi ID bo'yicha chiqishni qayd etish",
)
async def check_out_by_visitor(
    visitor_id: uuid.UUID,
    current_user: AllStaff,
    db: DbSession,
    payload: Annotated[CheckOutRequest | None, Body()] = None,
) -> VisitResponse:
    """Record exit for the visitor's currently open visit."""
    visit = await VisitService(db).check_out_by_visitor(visitor_id, current_user, payload)
    return VisitResponse.model_validate(visit)


@router.get(
    "/active",
    response_model=PaginatedResponse[VisitResponse],
    status_code=status.HTTP_200_OK,
    summary="Hozir binoda bo'lgan tashrifchilar",
)
async def list_active_visits(
    db: DbSession,
    pagination: PaginationDep,
    search: Annotated[
        str | None,
        Query(max_length=100, description="Ism yoki telefon raqami bo'yicha qidirish"),
    ] = None,
) -> PaginatedResponse[VisitResponse]:
    """List visitors currently inside the building."""
    return await VisitService(db).list_active_visits(pagination, search=search)


@router.get(
    "",
    response_model=PaginatedResponse[VisitResponse],
    status_code=status.HTTP_200_OK,
    summary="Tashriflar tarixi",
)
async def list_visits(
    db: DbSession,
    pagination: PaginationDep,
    visitor_id: Annotated[
        uuid.UUID | None,
        Query(description="Tashrifchi ID bo'yicha filtr"),
    ] = None,
    visit_status: Annotated[
        VisitStatus | None,
        Query(alias="status", description="Tashrif holati (inside / completed)"),
    ] = None,
    search: Annotated[
        str | None,
        Query(max_length=100, description="Tashrifchi ismi yoki telefoni bo'yicha qidirish"),
    ] = None,
    date_from: Annotated[date | None, Query(description="Boshlanish sanasi (YYYY-MM-DD)")] = None,
    date_to: Annotated[date | None, Query(description="Tugash sanasi (YYYY-MM-DD)")] = None,
) -> PaginatedResponse[VisitResponse]:
    """List visit history with optional filtering by visitor, status, search, and date range."""
    return await VisitService(db).list_visits(
        pagination,
        visitor_id=visitor_id,
        status=visit_status,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/{visit_id}",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
    summary="Tashrif tafsilotlari",
)
async def get_visit(
    visit_id: uuid.UUID,
    db: DbSession,
) -> VisitResponse:
    """Retrieve a single visit record by ID."""
    visit = await VisitService(db).get_visit(visit_id)
    return VisitResponse.model_validate(visit)
