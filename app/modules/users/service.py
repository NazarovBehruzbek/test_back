import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.common.pagination import PaginatedResponse, PaginationParams
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.core.security import hash_password, verify_password
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    PasswordChangeRequest,
    UserAdminUpdate,
    UserCreate,
    UserProfileUpdate,
    UserResponse,
)


class UserService:
    """Business logic for user creation, profile management, and role administration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = RefreshTokenRepository(session)

    @staticmethod
    def _ensure_can_assign_role(actor: User, target_role: UserRole) -> None:
        """Enforce role creation/assignment hierarchy."""
        if actor.role == UserRole.OPERATOR:
            raise ForbiddenError("Operator foydalanuvchilarni boshqarish huquqiga ega emas")
        if actor.role == UserRole.ADMIN and target_role != UserRole.OPERATOR:
            raise ForbiddenError("Admin faqat Operator rolini tayinlashi mumkin")

    async def create_user(self, payload: UserCreate, actor: User) -> User:
        """Create a new staff account subject to RBAC role hierarchy and unique email."""
        self._ensure_can_assign_role(actor, payload.role)

        normalized_email = str(payload.email).strip().lower()
        if await self.user_repo.get_by_email(normalized_email) is not None:
            raise ConflictError("Bu email bilan foydalanuvchi allaqachon mavjud")

        user = User(
            full_name=payload.full_name.strip(),
            email=normalized_email,
            phone=payload.phone,
            password_hash=hash_password(payload.password),
            role=payload.role,
            is_active=True,
        )
        try:
            await self.user_repo.add(user)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Bu email bilan foydalanuvchi allaqachon mavjud") from exc

        await self.session.refresh(user)
        return user

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """Retrieve a user by ID or raise NotFoundError."""
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Foydalanuvchi topilmadi")
        return user

    async def list_users(
        self,
        pagination: PaginationParams,
        *,
        role: UserRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[UserResponse]:
        """List users with pagination and optional filtering."""
        items, total = await self.user_repo.list_users(
            offset=pagination.offset,
            limit=pagination.size,
            role=role,
            is_active=is_active,
            search=search,
        )
        return PaginatedResponse.create(
            items=[UserResponse.model_validate(item) for item in items],
            total=total,
            page=pagination.page,
            size=pagination.size,
        )

    async def update_own_profile(
        self,
        current_user: User,
        payload: UserProfileUpdate,
    ) -> User:
        """Update the authenticated user's own profile fields."""
        fields = payload.model_fields_set
        if "full_name" in fields:
            if payload.full_name is None:
                raise BadRequestError("To'liq ism bo'sh bo'lishi mumkin emas")
            current_user.full_name = payload.full_name.strip()
        if "phone" in fields:
            current_user.phone = payload.phone

        await self.user_repo.save(current_user)
        await self.session.commit()
        await self.session.refresh(current_user)
        return current_user

    async def change_password(
        self,
        current_user: User,
        payload: PasswordChangeRequest,
    ) -> None:
        """Verify current password, set a new password hash, and revoke active sessions."""
        if not verify_password(payload.current_password, current_user.password_hash):
            raise BadRequestError("Joriy parol noto'g'ri")
        if payload.current_password == payload.new_password:
            raise BadRequestError("Yangi parol joriy paroldan farqli bo'lishi kerak")

        current_user.password_hash = hash_password(payload.new_password)
        await self.user_repo.save(current_user)
        await self.token_repo.revoke_all_for_user(current_user.id, datetime.now(UTC))
        await self.session.commit()

    async def update_user_by_admin(
        self,
        user_id: uuid.UUID,
        payload: UserAdminUpdate,
        actor: User,
    ) -> User:
        """Update another user's profile, role, or activation state with RBAC checks."""
        if actor.role == UserRole.OPERATOR:
            raise ForbiddenError("Operator foydalanuvchilarni tahrirlash huquqiga ega emas")

        target = await self.get_user_by_id(user_id)

        if actor.role == UserRole.ADMIN and target.role != UserRole.OPERATOR:
            raise ForbiddenError("Admin faqat Operator hisoblarini tahrirlashi mumkin")

        fields = payload.model_fields_set
        if "role" in fields:
            if payload.role is None:
                raise BadRequestError("Rol qiymati bo'sh bo'lishi mumkin emas")
            if target.id == actor.id and payload.role != target.role:
                raise BadRequestError("O'z rolingizni o'zgartira olmaysiz")
            self._ensure_can_assign_role(actor, payload.role)
            target.role = payload.role

        if "is_active" in fields:
            if payload.is_active is None:
                raise BadRequestError("Faollik holati bo'sh bo'lishi mumkin emas")
            if target.id == actor.id and not payload.is_active:
                raise BadRequestError("O'z hisobingizni bloklay olmaysiz")
            target.is_active = payload.is_active
            if not payload.is_active:
                await self.token_repo.revoke_all_for_user(target.id, datetime.now(UTC))

        if "full_name" in fields:
            if payload.full_name is None:
                raise BadRequestError("To'liq ism bo'sh bo'lishi mumkin emas")
            target.full_name = payload.full_name.strip()

        if "phone" in fields:
            target.phone = payload.phone

        await self.user_repo.save(target)
        await self.session.commit()
        await self.session.refresh(target)
        return target
