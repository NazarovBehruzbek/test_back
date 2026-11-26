from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credentials payload for user authentication."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    """Payload containing a refresh token to rotate."""

    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    """Payload containing the refresh token to revoke on logout."""

    refresh_token: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Access and refresh JWT pair returned after authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
