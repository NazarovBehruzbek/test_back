import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.validators import PhoneStr


class VisitorCreate(BaseModel):
    """Payload for registering a new visitor."""

    full_name: str = Field(..., min_length=2, max_length=150)
    phone: PhoneStr
    document_number: str | None = Field(default=None, max_length=50)
    organization: str | None = Field(default=None, max_length=150)
    notes: str | None = Field(default=None, max_length=1000)


class VisitorUpdate(BaseModel):
    """Payload for updating an existing visitor profile."""

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: PhoneStr | None = None
    document_number: str | None = Field(default=None, max_length=50)
    organization: str | None = Field(default=None, max_length=150)
    notes: str | None = Field(default=None, max_length=1000)


class VisitorResponse(BaseModel):
    """Visitor profile response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    phone: str
    document_number: str | None
    organization: str | None
    notes: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
