"""
Pydantic request/response models for the Chat API.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel


class ChatRequest(BaseModel):
    """Incoming chat request from the frontend."""

    # alias_generator auto-maps snake_case → camelCase (e.g. conversation_id → conversationId)
    # populate_by_name allows using either snake_case or camelCase
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    message: str
    conversation_id: str | None = "default"
    preferred_model: str | None = "auto"

    @field_validator("conversation_id", mode="before")
    @classmethod
    def coerce_conversation_id(cls, v: Any) -> Any:
        # The frontend sends Date.now() as a number for new conversations
        if v is not None:
            return str(v)
        return v


class ChatResponse(BaseModel):
    """Chat response sent back to the frontend."""

    text: str
    model: str
