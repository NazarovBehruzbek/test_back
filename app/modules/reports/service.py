import asyncio
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.datetime_utils import local_day_end_exclusive_utc, local_day_start_utc
from app.common.enums import VisitStatus
from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.modules.reports.exporters import build_visits_excel, build_visits_pdf
from app.modules.reports.repository import ReportsRepository
from app.modules.reports.schemas import ReportRowResponse, ReportSummaryResponse

_MAX_REPORT_DAYS = 366


class ReportsService:
    """Business logic for date-range visit reports and Excel/PDF exports."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReportsRepository(session)

    @staticmethod
    def _validate_range(start_date: date, end_date: date) -> None:
        """Ensure report start/end dates are ordered and within safe memory limits."""
        if start_date > end_date:
            raise BadRequestError("Boshlanish sanasi tugash sanasidan katta bo'lishi mumkin emas")
        if (end_date - start_date).days + 1 > _MAX_REPORT_DAYS:
            raise BadRequestError(
                f"Hisobot oralig'i ko'pi bilan {_MAX_REPORT_DAYS} kun bo'lishi mumkin"
            )

    async def get_report_summary(
        self,
        *,
        start_date: date,
        end_date: date,
        status: VisitStatus | None = None,
    ) -> ReportSummaryResponse:
        """Load and summarize visits for the selected local date range."""
        self._validate_range(start_date, end_date)
        tz = get_settings().tz

        visits = await self.repo.get_visits_for_report(
            start_utc=local_day_start_utc(start_date, tz),
            end_exclusive_utc=local_day_end_exclusive_utc(end_date, tz),
            status=status,
        )

        rows: list[ReportRowResponse] = []
        completed_count = 0
        inside_count = 0

        for visit in visits:
            duration_minutes: int | None = None
            if visit.checked_out_at is not None:
                duration_minutes = max(
                    0,
                    int((visit.checked_out_at - visit.checked_in_at).total_seconds() // 60),
                )
                completed_count += 1
            else:
                inside_count += 1

            rows.append(
                ReportRowResponse(
                    visit_id=visit.id,
                    visitor_name=visit.visitor.full_name,
                    visitor_phone=visit.visitor.phone,
                    organization=visit.visitor.organization,
                    purpose=visit.purpose,
                    host_name=visit.host_name,
                    badge_number=visit.badge_number,
                    checked_in_at=visit.checked_in_at,
                    checked_out_at=visit.checked_out_at,
                    duration_minutes=duration_minutes,
                    status=visit.status,
                    checked_in_by_name=(
                        visit.check_in_operator.full_name if visit.check_in_operator else None
                    ),
                    checked_out_by_name=(
                        visit.check_out_operator.full_name if visit.check_out_operator else None
                    ),
                )
            )

        return ReportSummaryResponse(
            start_date=start_date,
            end_date=end_date,
            total_visits=len(rows),
            completed_visits=completed_count,
            currently_inside=inside_count,
            items=rows,
        )

    async def export_excel(
        self,
        *,
        start_date: date,
        end_date: date,
        status: VisitStatus | None = None,
    ) -> tuple[bytes, str]:
        """Generate an Excel (.xlsx) report off the async event loop."""
        summary = await self.get_report_summary(
            start_date=start_date,
            end_date=end_date,
            status=status,
        )
        tz = get_settings().tz
        content = await asyncio.to_thread(build_visits_excel, summary, tz)
        filename = f"visits_report_{start_date}_{end_date}.xlsx"
        return content, filename

    async def export_pdf(
        self,
        *,
        start_date: date,
        end_date: date,
        status: VisitStatus | None = None,
    ) -> tuple[bytes, str]:
        """Generate a PDF (.pdf) report off the async event loop."""
        summary = await self.get_report_summary(
            start_date=start_date,
            end_date=end_date,
            status=status,
        )
        tz = get_settings().tz
        content = await asyncio.to_thread(build_visits_pdf, summary, tz)
        filename = f"visits_report_{start_date}_{end_date}.pdf"
        return content, filename
