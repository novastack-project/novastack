from typing import Any

from novastack.core.bridge.pydantic import BaseModel, Field
from novastack.core.llms.enums import MessageRole


class ChatMessage(BaseModel):
    """Chat message."""

    model_config = {"use_enum_values": True}

    role: MessageRole | str = Field(
        ..., description="Role of the message sender (system, user, assistant, or tool)"
    )
    content: str | None = Field(default=None, description="Content of the message")

    def to_dict(self) -> dict:
        """Convert ChatMessage to dict."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_value(cls, value: dict) -> "ChatMessage":
        if value is None:
            raise ValueError("Unexpected 'ChatMessage', cannot be None")

        if isinstance(value, cls):
            return value

        if isinstance(value, dict):
            try:
                return cls.model_validate(value)
            except Exception as e:
                raise ValueError(f"Unexpected 'ChatMessage' dict. Received: '{e}'.")

        raise TypeError(
            f"Unexpected 'ChatMessage' type. Expected dict or ChatMessage, but received {type(value).__name__}."
        )


class ChatResponse(BaseModel):
    """Chat completion response."""

    message: ChatMessage = Field(..., description="The generated chat message response")
    input_token_count: int | None = Field(
        default=None, ge=0, description="Number of tokens in the input"
    )
    generated_token_count: int | None = Field(
        default=None, ge=0, description="Number of tokens generated in the response"
    )
    raw: Any | None = Field(
        default=None, description="Raw response from the LLM provider"
    )


class CompletionResponse(BaseModel):
    """Completion response."""

    text: str = Field(..., min_length=1, description="Generated text response")
    input_token_count: int | None = Field(
        default=None, ge=0, description="Number of tokens in the input"
    )
    generated_token_count: int | None = Field(
        default=None, ge=0, description="Number of tokens generated in the response"
    )
    raw: Any | None = Field(
        default=None, description="Raw response from the LLM provider"
    )
