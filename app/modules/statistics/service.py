from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import local_day_end_exclusive_utc, local_day_start_utc
from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.modules.statistics.repository import StatisticsRepository
from app.modules.statistics.schemas import DailyVisitStatResponse, OverviewStatsResponse

_MAX_DAILY_RANGE_DAYS = 90


class StatisticsService:
    """Business logic for calculating dashboard and daily trend statistics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = StatisticsRepository(session)

    async def get_overview(self) -> OverviewStatsResponse:
        """Compute today, weekly, monthly, total visitor, and live inside counts."""
        settings = get_settings()
        tz = settings.tz
        now_utc = datetime.now(UTC)
        local_today = now_utc.astimezone(tz).date()

        today_start = local_day_start_utc(local_today, tz)
        tomorrow_start = local_day_end_exclusive_utc(local_today, tz)
        week_start_date = local_today - timedelta(days=local_today.weekday())
        week_start = local_day_start_utc(week_start_date, tz)
        month_start_date = local_today.replace(day=1)
        month_start = local_day_start_utc(month_start_date, tz)

        counts = await self.repo.get_overview_counts(
            today_start=today_start,
            week_start=week_start,
            month_start=month_start,
            tomorrow_start=tomorrow_start,
        )

        return OverviewStatsResponse(
            today_visits=counts.today_visits,
            weekly_visits=counts.weekly_visits,
            monthly_visits=counts.monthly_visits,
            total_visitors=counts.total_visitors,
            currently_inside=counts.currently_inside,
            timezone=settings.TIMEZONE,
            generated_at=now_utc,
        )

    async def get_daily_stats(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[DailyVisitStatResponse]:
        """Return continuous daily visit counts for a local date range (default: last 7 days)."""
        settings = get_settings()
        tz = settings.tz
        local_today = datetime.now(UTC).astimezone(tz).date()

        resolved_to = date_to or local_today
        resolved_from = date_from or (resolved_to - timedelta(days=6))

        if resolved_from > resolved_to:
            raise BadRequestError("Boshlanish sanasi tugash sanasidan katta bo'lishi mumkin emas")
        if (resolved_to - resolved_from).days + 1 > _MAX_DAILY_RANGE_DAYS:
            raise BadRequestError(
                f"Kunlik statistika oralig'i ko'pi bilan "
                f"{_MAX_DAILY_RANGE_DAYS} kun bo'lishi mumkin"
            )

        counts_by_day = await self.repo.get_daily_counts(
            start_utc=local_day_start_utc(resolved_from, tz),
            end_exclusive_utc=local_day_end_exclusive_utc(resolved_to, tz),
            timezone_name=settings.TIMEZONE,
        )

        series: list[DailyVisitStatResponse] = []
        current_day = resolved_from
        while current_day <= resolved_to:
            series.append(
                DailyVisitStatResponse(
                    date=current_day,
                    visits_count=counts_by_day.get(current_day, 0),
                )
            )
            current_day += timedelta(days=1)
        return series
