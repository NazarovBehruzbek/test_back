from typing import Any


class AppException(Exception):
    """Base application exception translated to a structured JSON error response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str = "APP_ERROR",
        details: Any = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)


class BadRequestError(AppException):
    """Raised when the client request violates business input rules."""

    def __init__(self, message: str = "Noto'g'ri so'rov", details: Any = None) -> None:
        super().__init__(message, status_code=400, code="BAD_REQUEST", details=details)


class UnauthorizedError(AppException):
    """Raised when authentication credentials are missing, invalid, or expired."""

    def __init__(self, message: str = "Avtorizatsiya talab qilinadi", details: Any = None) -> None:
        super().__init__(message, status_code=401, code="UNAUTHORIZED", details=details)


class ForbiddenError(AppException):
    """Raised when the authenticated user lacks permission for the operation."""

    def __init__(
        self,
        message: str = "Ushbu amalni bajarish uchun ruxsat yo'q",
        details: Any = None,
    ) -> None:
        super().__init__(message, status_code=403, code="FORBIDDEN", details=details)


class NotFoundError(AppException):
    """Raised when a requested domain entity does not exist."""

    def __init__(self, message: str = "Ma'lumot topilmadi", details: Any = None) -> None:
        super().__init__(message, status_code=404, code="NOT_FOUND", details=details)


class ConflictError(AppException):
    """Raised when an operation conflicts with existing state or uniqueness rules."""

    def __init__(self, message: str = "Ma'lumotlar ziddiyati", details: Any = None) -> None:
        super().__init__(message, status_code=409, code="CONFLICT", details=details)
