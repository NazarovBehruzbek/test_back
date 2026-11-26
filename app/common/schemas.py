from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Standard single-message API response."""

    message: str
