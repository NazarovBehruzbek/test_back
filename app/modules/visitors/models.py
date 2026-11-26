import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.visits.models import Visit


class Visitor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Registered building visitor profile with soft-delete support."""

    __tablename__ = "visitors"

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    document_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(150), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator: Mapped["User | None"] = relationship(foreign_keys=[created_by])
    visits: Mapped[list["Visit"]] = relationship(back_populates="visitor")

    # Note: GIN trigram indexes require the PostgreSQL `pg_trgm` extension.
    __table_args__ = (
        Index(
            "uq_visitors_phone_active",
            "phone",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_visitors_deleted_at", "deleted_at"),
        Index(
            "ix_visitors_full_name_trgm",
            "full_name",
            postgresql_using="gin",
            postgresql_ops={"full_name": "gin_trgm_ops"},
        ),
        Index(
            "ix_visitors_phone_trgm",
            "phone",
            postgresql_using="gin",
            postgresql_ops={"phone": "gin_trgm_ops"},
        ),
    )

    @property
    def is_deleted(self) -> bool:
        """Return True if the visitor has been soft-deleted."""
        return self.deleted_at is not None

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone})"
