from enum import StrEnum


class UserRole(StrEnum):
    """System user roles for RBAC authorization."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATOR = "operator"


class VisitStatus(StrEnum):
    """Computed status of a visitor's visit record."""

    INSIDE = "inside"
    COMPLETED = "completed"
