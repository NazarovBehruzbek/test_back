from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.dependencies import DbSession
from app.modules.statistics.schemas import DailyVisitStatResponse, OverviewStatsResponse
from app.modules.statistics.service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get(
    "/overview",
    response_model=OverviewStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Umumiy statistika (bugungi, haftalik, oylik, binodagilar)",
)
async def get_overview_statistics(
    db: DbSession,
) -> OverviewStatsResponse:
    """Return real-time visit and visitor summary statistics."""
    return await StatisticsService(db).get_overview()


@router.get(
    "/daily",
    response_model=list[DailyVisitStatResponse],
    status_code=status.HTTP_200_OK,
    summary="Kunlik tashriflar statistikasi",
)
async def get_daily_statistics(
    db: DbSession,
    date_from: Annotated[date | None, Query(description="Boshlanish sanasi (YYYY-MM-DD)")] = None,
    date_to: Annotated[date | None, Query(description="Tugash sanasi (YYYY-MM-DD)")] = None,
) -> list[DailyVisitStatResponse]:
    """Return daily visit counts over the selected date range (defaults to last 7 days)."""
    return await StatisticsService(db).get_daily_stats(
        date_from=date_from,
        date_to=date_to,
    )
