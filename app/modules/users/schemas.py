import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.common.enums import UserRole
from app.common.validators import PhoneStr


class UserCreate(BaseModel):
    """Payload for creating a new system user (Admin/Operator)."""

    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: PhoneStr | None = None
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.OPERATOR


class UserProfileUpdate(BaseModel):
    """Payload for an authenticated user updating their own profile."""

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: PhoneStr | None = None


class UserAdminUpdate(BaseModel):
    """Payload for an authorized administrator updating another user."""

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: PhoneStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class PasswordChangeRequest(BaseModel):
    """Payload for changing the authenticated user's password."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Public user representation without sensitive credentials."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    phone: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
