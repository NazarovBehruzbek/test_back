import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.common.enums import UserRole
from app.common.pagination import PaginatedResponse
from app.common.schemas import MessageResponse
from app.core.dependencies import AdminOrSuperAdmin, CurrentUser, DbSession, PaginationDep
from app.modules.users.schemas import (
    PasswordChangeRequest,
    UserAdminUpdate,
    UserCreate,
    UserProfileUpdate,
    UserResponse,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Shaxsiy profilni ko'rish",
)
async def get_my_profile(current_user: CurrentUser) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Shaxsiy profilni tahrirlash",
)
async def update_my_profile(
    payload: UserProfileUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """Update the authenticated user's full name or phone number."""
    user = await UserService(db).update_own_profile(current_user, payload)
    return UserResponse.model_validate(user)


@router.post(
    "/me/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Parolni o'zgartirish",
)
async def change_my_password(
    payload: PasswordChangeRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Change the authenticated user's password and revoke active refresh tokens."""
    await UserService(db).change_password(current_user, payload)
    return MessageResponse(message="Parol muvaffaqiyatli o'zgartirildi")


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi foydalanuvchi yaratish (Admin / Super Admin)",
)
async def create_user(
    payload: UserCreate,
    current_user: AdminOrSuperAdmin,
    db: DbSession,
) -> UserResponse:
    """Create a new system staff account."""
    user = await UserService(db).create_user(payload, current_user)
    return UserResponse.model_validate(user)


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Foydalanuvchilar ro'yxati",
)
async def list_users(
    db: DbSession,
    pagination: PaginationDep,
    role: Annotated[UserRole | None, Query(description="Rol bo'yicha filtr")] = None,
    is_active: Annotated[bool | None, Query(description="Faollik holati")] = None,
    search: Annotated[
        str | None,
        Query(max_length=100, description="Ism yoki email qidiruvi"),
    ] = None,
) -> PaginatedResponse[UserResponse]:
    """List staff accounts with pagination and optional filters."""
    return await UserService(db).list_users(
        pagination,
        role=role,
        is_active=is_active,
        search=search,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Foydalanuvchi ma'lumotini ko'rish",
)
async def get_user(
    user_id: uuid.UUID,
    db: DbSession,
) -> UserResponse:
    """Retrieve a staff account by ID."""
    user = await UserService(db).get_user_by_id(user_id)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Foydalanuvchini tahrirlash (Admin / Super Admin)",
)
async def update_user(
    user_id: uuid.UUID,
    payload: UserAdminUpdate,
    current_user: AdminOrSuperAdmin,
    db: DbSession,
) -> UserResponse:
    """Update another user's profile, role, or active status."""
    user = await UserService(db).update_user_by_admin(user_id, payload, current_user)
    return UserResponse.model_validate(user)
