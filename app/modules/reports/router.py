from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.common.enums import VisitStatus
from app.core.dependencies import DbSession
from app.modules.reports.schemas import ReportSummaryResponse
from app.modules.reports.service import ReportsService

router = APIRouter(prefix="/reports", tags=["Reports"])

_EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/visits",
    response_model=ReportSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Sana oralig'i bo'yicha hisobot (JSON)",
)
async def get_visits_report(
    db: DbSession,
    start_date: Annotated[date, Query(description="Boshlanish sanasi (YYYY-MM-DD)")],
    end_date: Annotated[date, Query(description="Tugash sanasi (YYYY-MM-DD)")],
    visit_status: Annotated[
        VisitStatus | None,
        Query(alias="status", description="Tashrif holati (inside / completed)"),
    ] = None,
) -> ReportSummaryResponse:
    """Return structured report data for the specified date range."""
    return await ReportsService(db).get_report_summary(
        start_date=start_date,
        end_date=end_date,
        status=visit_status,
    )


@router.get(
    "/export/excel",
    status_code=status.HTTP_200_OK,
    summary="Hisobotni Excel (.xlsx) formatida eksport qilish",
)
async def export_visits_excel(
    db: DbSession,
    start_date: Annotated[date, Query(description="Boshlanish sanasi (YYYY-MM-DD)")],
    end_date: Annotated[date, Query(description="Tugash sanasi (YYYY-MM-DD)")],
    visit_status: Annotated[
        VisitStatus | None,
        Query(alias="status", description="Tashrif holati (inside / completed)"),
    ] = None,
) -> Response:
    """Download visit report for the selected date range as an Excel (.xlsx) file."""
    content, filename = await ReportsService(db).export_excel(
        start_date=start_date,
        end_date=end_date,
        status=visit_status,
    )
    return Response(
        content=content,
        media_type=_EXCEL_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/export/pdf",
    status_code=status.HTTP_200_OK,
    summary="Hisobotni PDF (.pdf) formatida eksport qilish",
)
async def export_visits_pdf(
    db: DbSession,
    start_date: Annotated[date, Query(description="Boshlanish sanasi (YYYY-MM-DD)")],
    end_date: Annotated[date, Query(description="Tugash sanasi (YYYY-MM-DD)")],
    visit_status: Annotated[
        VisitStatus | None,
        Query(alias="status", description="Tashrif holati (inside / completed)"),
    ] = None,
) -> Response:
    """Download visit report for the selected date range as a PDF (.pdf) file."""
    content, filename = await ReportsService(db).export_pdf(
        start_date=start_date,
        end_date=end_date,
        status=visit_status,
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
