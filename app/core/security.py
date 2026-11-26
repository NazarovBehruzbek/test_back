import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.common.enums import UserRole
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

TokenType = Literal["access", "refresh"]

_password_hasher = PasswordHash((Argon2Hasher(),))
# Precomputed dummy hash used to keep failed-login timing uniform when an email is unknown.
_DUMMY_PASSWORD_HASH = _password_hasher.hash("dummy-timing-protection-password")


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """Validated claims extracted from a decoded JWT."""

    user_id: uuid.UUID
    token_type: TokenType
    role: UserRole | None
    jti: str
    expires_at: datetime


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored Argon2id hash."""
    return _password_hasher.verify(plain_password, password_hash)


def verify_dummy_password(plain_password: str) -> None:
    """Run Argon2id verification against a dummy hash to mitigate user enumeration timing."""
    _password_hasher.verify(plain_password, _DUMMY_PASSWORD_HASH)


def hash_token(raw_token: str) -> str:
    """Return a SHA-256 hex digest of a raw refresh token for safe database storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(user_id: uuid.UUID, role: UserRole) -> str:
    """Create a short-lived signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, datetime]:
    """Create a long-lived signed JWT refresh token and return (token, expires_at)."""
    settings = get_settings()
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_at


def decode_token(token: str, expected_type: TokenType) -> TokenPayload:
    """Decode and validate a JWT signature, expiration, subject, and token type."""
    settings = get_settings()
    try:
        raw_payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "type", "jti"]},
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Token yaroqsiz yoki muddati tugagan") from exc

    token_type = raw_payload.get("type")
    if token_type != expected_type:
        raise UnauthorizedError("Noto'g'ri token turi")

    try:
        user_id = uuid.UUID(str(raw_payload["sub"]))
        expires_at = datetime.fromtimestamp(float(raw_payload["exp"]), tz=UTC)
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Token tarkibi yaroqsiz") from exc

    role_value = raw_payload.get("role")
    role: UserRole | None = None
    if role_value is not None:
        try:
            role = UserRole(str(role_value))
        except ValueError as exc:
            raise UnauthorizedError("Token roli yaroqsiz") from exc

    return TokenPayload(
        user_id=user_id,
        token_type=expected_type,
        role=role,
        jti=str(raw_payload["jti"]),
        expires_at=expires_at,
    )
