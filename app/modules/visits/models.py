import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import VisitStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.visitors.models import Visitor


class Visit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Visitor check-in and check-out event record."""

    __tablename__ = "visits"

    visitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("visitors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    checked_in_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    checked_out_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    host_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    badge_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    visitor: Mapped["Visitor"] = relationship(back_populates="visits")
    check_in_operator: Mapped["User | None"] = relationship(foreign_keys=[checked_in_by])
    check_out_operator: Mapped["User | None"] = relationship(foreign_keys=[checked_out_by])

    __table_args__ = (
        CheckConstraint(
            "checked_out_at IS NULL OR checked_out_at >= checked_in_at",
            name="check_out_after_check_in",
        ),
        Index(
            "uq_visits_one_active_per_visitor",
            "visitor_id",
            unique=True,
            postgresql_where=text("checked_out_at IS NULL"),
        ),
        Index(
            "ix_visits_active",
            checked_in_at.desc(),
            postgresql_where=text("checked_out_at IS NULL"),
        ),
        Index("ix_visits_checked_in_at", checked_in_at.desc()),
        Index("ix_visits_visitor_id", "visitor_id"),
    )

    @property
    def is_inside(self) -> bool:
        """Return True if the visitor has not checked out yet."""
        return self.checked_out_at is None

    @property
    def status(self) -> VisitStatus:
        """Return current visit lifecycle status."""
        return VisitStatus.INSIDE if self.checked_out_at is None else VisitStatus.COMPLETED
