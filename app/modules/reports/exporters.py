from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from fpdf import FPDF
from fpdf.fonts import FontFace
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.common.enums import VisitStatus
from app.modules.reports.schemas import ReportRowResponse, ReportSummaryResponse

_REPORT_HEADERS = (
    "#",
    "Tashrifchi",
    "Telefon",
    "Tashkilot",
    "Maqsad",
    "Qabul qiluvchi",
    "Kelgan vaqti",
    "Ketgan vaqti",
    "Davomiylik",
    "Holat",
)

_FONT_CANDIDATES: tuple[tuple[Path, Path], ...] = (
    (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ),
    (
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
    ),
    (
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    ),
)


def _format_dt(value: datetime | None, tz: ZoneInfo) -> str:
    """Format an optional timezone-aware datetime in the configured local timezone."""
    if value is None:
        return "—"
    return value.astimezone(tz).strftime("%Y-%m-%d %H:%M")


def _format_status(status: VisitStatus) -> str:
    """Translate VisitStatus enum into Uzbek display text."""
    return "Binoda" if status == VisitStatus.INSIDE else "Chiqib ketgan"


def _format_row(index: int, row: ReportRowResponse, tz: ZoneInfo) -> list[str]:
    """Convert a ReportRowResponse into ordered display strings shared across exporters."""
    duration = f"{row.duration_minutes} daq" if row.duration_minutes is not None else "—"
    return [
        str(index),
        row.visitor_name,
        row.visitor_phone,
        row.organization or "—",
        row.purpose or "—",
        row.host_name or "—",
        _format_dt(row.checked_in_at, tz),
        _format_dt(row.checked_out_at, tz),
        duration,
        _format_status(row.status),
    ]


def _sanitize_excel_cell(value: str, *, is_phone: bool = False) -> str:
    """Prevent spreadsheet formula injection in user-supplied text fields."""
    if is_phone:
        return value
    if value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{value}"
    return value


def build_visits_excel(summary: ReportSummaryResponse, tz: ZoneInfo) -> bytes:
    """Render a styled Excel (.xlsx) report from ReportSummaryResponse."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Tashriflar hisoboti"

    title = f"AqlliOlam — Tashriflar hisoboti ({summary.start_date} — {summary.end_date})"
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(_REPORT_HEADERS))
    title_cell = sheet.cell(row=1, column=1, value=title)
    title_cell.font = Font(size=13, bold=True, color="1E293B")
    title_cell.alignment = Alignment(horizontal="left", vertical="center")
    sheet.row_dimensions[1].height = 24

    meta_text = (
        f"Jami tashriflar: {summary.total_visits}  |  "
        f"Chiqib ketgan: {summary.completed_visits}  |  "
        f"Hozir binoda: {summary.currently_inside}"
    )
    sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(_REPORT_HEADERS))
    meta_cell = sheet.cell(row=2, column=1, value=meta_text)
    meta_cell.font = Font(size=10, italic=True, color="475569")
    sheet.row_dimensions[2].height = 18

    header_row_idx = 4
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    for col_idx, heading in enumerate(_REPORT_HEADERS, start=1):
        cell = sheet.cell(row=header_row_idx, column=col_idx, value=heading)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    sheet.row_dimensions[header_row_idx].height = 22

    for idx, item in enumerate(summary.items, start=1):
        row_values = _format_row(idx, item, tz)
        excel_row = header_row_idx + idx
        for col_idx, raw_value in enumerate(row_values, start=1):
            is_phone = col_idx == 3
            safe_val = _sanitize_excel_cell(raw_value, is_phone=is_phone)
            cell = sheet.cell(row=excel_row, column=col_idx, value=safe_val)
            cell.data_type = "s"
            cell.alignment = Alignment(
                horizontal="center" if col_idx in (1, 7, 8, 9, 10) else "left",
                vertical="center",
            )

    sheet.freeze_panes = f"A{header_row_idx + 1}"
    last_row = max(header_row_idx, header_row_idx + len(summary.items))
    sheet.auto_filter.ref = f"A{header_row_idx}:{get_column_letter(len(_REPORT_HEADERS))}{last_row}"

    for col_idx in range(1, len(_REPORT_HEADERS) + 1):
        max_len = len(_REPORT_HEADERS[col_idx - 1])
        for row_idx in range(header_row_idx + 1, last_row + 1):
            val = sheet.cell(row=row_idx, column=col_idx).value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        sheet.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 38)

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


class _ReportPDF(FPDF):
    """Landscape PDF layout with automatic page footer numbering."""

    def __init__(self, font_family: str) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self._font_family = font_family

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(self._font_family, size=8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, f"Sahifa {self.page_no()}/{{nb}}", align="R")


def _configure_pdf_font(pdf: FPDF) -> tuple[str, bool]:
    """Register a cross-platform Unicode TTF font if available, else fall back to Helvetica."""
    for regular_path, bold_path in _FONT_CANDIDATES:
        if regular_path.is_file():
            pdf.add_font("AppUnicode", "", str(regular_path))
            bold_target = bold_path if bold_path.is_file() else regular_path
            pdf.add_font("AppUnicode", "B", str(bold_target))
            return "AppUnicode", True
    return "Helvetica", False


def _pdf_safe(text: str, unicode_enabled: bool) -> str:
    """Replace unsupported glyphs when falling back to core Latin-1 PDF fonts."""
    if unicode_enabled:
        return text
    return text.encode("latin-1", "replace").decode("latin-1")


def build_visits_pdf(summary: ReportSummaryResponse, tz: ZoneInfo) -> bytes:
    """Render a formatted landscape A4 PDF report from ReportSummaryResponse."""
    pdf = _ReportPDF("Helvetica")
    font_family, unicode_enabled = _configure_pdf_font(pdf)
    pdf._font_family = font_family

    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(10, 12, 10)
    pdf.add_page()

    pdf.set_font(font_family, "B", 14)
    pdf.set_text_color(30, 41, 59)
    title = f"AqlliOlam — Tashriflar hisoboti ({summary.start_date} — {summary.end_date})"
    pdf.cell(0, 8, _pdf_safe(title, unicode_enabled), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(font_family, "", 9)
    pdf.set_text_color(71, 85, 105)
    meta = (
        f"Jami tashriflar: {summary.total_visits}  |  "
        f"Chiqib ketgan: {summary.completed_visits}  |  "
        f"Hozir binoda: {summary.currently_inside}"
    )
    pdf.cell(0, 6, _pdf_safe(meta, unicode_enabled), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font(font_family, "", 8)
    pdf.set_text_color(15, 23, 42)
    headings_style = FontFace(
        emphasis="BOLD",
        color=(255, 255, 255),
        fill_color=(30, 58, 138),
    )
    col_widths = (9, 36, 28, 32, 34, 30, 30, 30, 20, 28)

    with pdf.table(
        col_widths=col_widths,
        headings_style=headings_style,
        line_height=5.5,
        cell_fill_color=(248, 250, 252),
        cell_fill_mode="ROWS",
        borders_layout="HORIZONTAL_LINES",
    ) as table:
        header_row = table.row()
        for heading in _REPORT_HEADERS:
            header_row.cell(_pdf_safe(heading, unicode_enabled))

        if not summary.items:
            empty_row = table.row()
            empty_row.cell(
                _pdf_safe("Tanlangan sana oralig'ida tashriflar topilmadi.", unicode_enabled),
                colspan=len(_REPORT_HEADERS),
            )
        else:
            for idx, item in enumerate(summary.items, start=1):
                data_row = table.row()
                for val in _format_row(idx, item, tz):
                    data_row.cell(_pdf_safe(val, unicode_enabled))

    return bytes(pdf.output())
