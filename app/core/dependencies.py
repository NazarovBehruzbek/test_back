from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.common.pagination import PaginationParams
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_session_factory
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Provide an async SQLAlchemy session per request with rollback safety."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Authenticate the request via Bearer access token and return the active User."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Avtorizatsiya tokeni taqdim etilmadi")

    payload = decode_token(credentials.credentials, expected_type="access")
    user = await UserRepository(db).get_by_id(payload.user_id)
    if user is None:
        raise UnauthorizedError("Foydalanuvchi topilmadi")
    if not user.is_active:
        raise ForbiddenError("Foydalanuvchi hisobi faol emas")
    return user


def get_pagination(
    page: Annotated[int, Query(ge=1, description="Sahifa raqami")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Sahifadagi yozuvlar soni")] = 20,
) -> PaginationParams:
    """Build validated pagination parameters from query strings."""
    return PaginationParams(page=page, size=size)


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
PaginationDep = Annotated[PaginationParams, Depends(get_pagination)]


def require_roles(
    *allowed_roles: UserRole,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Create a dependency enforcing that the authenticated user has one of allowed_roles."""
    allowed_set = frozenset(allowed_roles)

    async def _role_checker(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_set:
            raise ForbiddenError("Ushbu amalni bajarish uchun sizning rolingizda ruxsat yo'q")
        return current_user

    return _role_checker


AllStaff = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.OPERATOR)),
]
AdminOrSuperAdmin = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
]
SuperAdminOnly = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN)),
]
