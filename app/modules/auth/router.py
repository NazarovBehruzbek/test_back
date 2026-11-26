from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import MessageResponse
from app.core.dependencies import get_current_user, get_db
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.modules.auth.service import AuthService
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Tizimga kirish",
)
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate with email and password to receive access and refresh JWT tokens."""
    return await AuthService(db).login(payload.email, payload.password)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Tokenlarni yangilash",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Exchange a valid refresh token for a newly rotated token pair."""
    return await AuthService(db).refresh(payload.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Tizimdan chiqish",
)
async def logout(
    payload: LogoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Revoke the active refresh token for the current session."""
    await AuthService(db).logout(payload.refresh_token, current_user.id)
    return MessageResponse(message="Tizimdan muvaffaqiyatli chiqildi")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Barcha sessiyalardan chiqish",
)
async def logout_all(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Revoke all active sessions belonging to the authenticated user."""
    revoked_count = await AuthService(db).logout_all(current_user.id)
    return MessageResponse(message=f"{revoked_count} ta faol sessiya yakunlandi")
