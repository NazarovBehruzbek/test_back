import math

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Query pagination parameters shared across list endpoints."""

    page: int = Field(default=1, ge=1, description="Sahifa raqami (1 dan boshlanadi)")
    size: int = Field(default=20, ge=1, le=100, description="Har bir sahifadagi yozuvlar soni")

    @property
    def offset(self) -> int:
        """Compute SQL OFFSET from 1-based page and size."""
        return (self.page - 1) * self.size


class PaginatedResponse[T](BaseModel):
    """Standard paginated list response container."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(
        cls,
        *,
        items: list[T],
        total: int,
        page: int,
        size: int,
    ) -> "PaginatedResponse[T]":
        """Build a PaginatedResponse and compute total page count."""
        pages = math.ceil(total / size) if total > 0 else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)
