import re
from typing import Annotated

from pydantic import AfterValidator

_PHONE_STRIP_RE = re.compile(r"[\s\-\(\)]")
_PHONE_VALID_RE = re.compile(r"^\+?[1-9]\d{6,14}$")
_UZ_LOCAL_RE = re.compile(r"^998\d{9}$")


def normalize_phone(value: str) -> str:
    """Normalize and validate phone numbers into a consistent E.164-like format."""
    cleaned = _PHONE_STRIP_RE.sub("", value.strip())
    if _UZ_LOCAL_RE.match(cleaned):
        cleaned = f"+{cleaned}"
    if not _PHONE_VALID_RE.match(cleaned):
        raise ValueError("Telefon raqami formati noto'g'ri (masalan: +998901234567)")
    return cleaned


PhoneStr = Annotated[str, AfterValidator(normalize_phone)]


def escape_like(term: str) -> str:
    """Escape SQL LIKE/ILIKE wildcard characters in user-supplied search strings."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def clean_optional_text(value: str | None) -> str | None:
    """Trim optional strings and normalize blank values to None."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
