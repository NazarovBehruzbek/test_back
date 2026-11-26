import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_dummy_password,
    verify_password,
)
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.auth.schemas import TokenResponse
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


class AuthService:
    """Business logic for login, token refresh rotation, and logout."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = RefreshTokenRepository(session)

    async def _issue_token_pair(self, user: User) -> TokenResponse:
        """Create and persist a fresh access/refresh token pair for an authenticated user."""
        settings = get_settings()
        access_token = create_access_token(user.id, user.role)
        refresh_token, refresh_expires_at = create_refresh_token(user.id)

        await self.token_repo.create(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=refresh_expires_at,
        )
        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def login(self, email: str, password: str) -> TokenResponse:
        """Authenticate a user by email and password and return a JWT pair."""
        user = await self.user_repo.get_by_email(email)
        if user is None:
            verify_dummy_password(password)
            raise UnauthorizedError("Email yoki parol noto'g'ri")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Email yoki parol noto'g'ri")

        if not user.is_active:
            raise ForbiddenError("Hisobingiz faol emas. Administratorga murojaat qiling")

        return await self._issue_token_pair(user)

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:
        """Rotate a valid refresh token and revoke all sessions if token reuse is detected."""
        decode_token(raw_refresh_token, expected_type="refresh")
        token_hash = hash_token(raw_refresh_token)
        stored = await self.token_repo.get_by_token_hash(token_hash)

        if stored is None:
            raise UnauthorizedError("Refresh token topilmadi")

        now = datetime.now(UTC)
        if stored.is_revoked:
            # Reuse of an already rotated/revoked token indicates potential theft.
            await self.token_repo.revoke_all_for_user(stored.user_id, now)
            await self.session.commit()
            raise UnauthorizedError("Refresh token allaqachon bekor qilingan")

        if stored.expires_at <= now:
            raise UnauthorizedError("Refresh token muddati tugagan")

        user = await self.user_repo.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Foydalanuvchi topilmadi yoki faol emas")

        await self.token_repo.revoke(stored, now)
        return await self._issue_token_pair(user)

    async def logout(self, raw_refresh_token: str, current_user_id: uuid.UUID) -> None:
        """Revoke the provided refresh token belonging to the authenticated user."""
        token_hash = hash_token(raw_refresh_token)
        stored = await self.token_repo.get_by_token_hash(token_hash)
        if stored is None:
            return

        if stored.user_id != current_user_id:
            raise ForbiddenError("Boshqa foydalanuvchi sessiyasini yopish mumkin emas")

        if not stored.is_revoked:
            await self.token_repo.revoke(stored, datetime.now(UTC))
            await self.session.commit()

    async def logout_all(self, current_user_id: uuid.UUID) -> int:
        """Revoke every active refresh token for the authenticated user."""
        revoked_count = await self.token_repo.revoke_all_for_user(
            current_user_id,
            datetime.now(UTC),
        )
        await self.session.commit()
        return revoked_count
