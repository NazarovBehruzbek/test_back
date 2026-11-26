import uuid
from datetime import datetime

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RefreshToken


class RefreshTokenRepository:
    """Data access layer for persisted refresh tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Persist a hashed refresh token record."""
        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Look up a refresh token record by its SHA-256 hash."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken, revoked_at: datetime) -> None:
        """Mark a single refresh token as revoked."""
        token.revoked_at = revoked_at
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID, revoked_at: datetime) -> int:
        """Revoke all active refresh tokens belonging to a user."""
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        result = await self.session.execute(stmt)
        if isinstance(result, CursorResult):
            return int(result.rowcount or 0)
        return 0
