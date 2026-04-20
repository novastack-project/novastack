from typing import Any

from novastack.core.bridge.pydantic import BaseModel, Field
from novastack.core.llms.enums import MessageRole


class ChatMessage(BaseModel):
    """Chat message."""

    model_config = {"use_enum_values": True}

    role: MessageRole = Field(
        ..., description="Role of the message sender (system, user, assistant, or tool)"
    )
    content: str | None = Field(default=None, description="Content of the message")

    def to_dict(self) -> dict:
        """Convert ChatMessage to dict."""
        return self.model_dump(exclude_none=True)


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
