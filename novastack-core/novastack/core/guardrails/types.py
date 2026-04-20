from typing import Any

from novastack.core.bridge.pydantic import (
    BaseModel,
    Field,
)
from novastack.core.guardrails.enums import Action


class GuardrailResponse(BaseModel):
    """
    Guardrail response model.

    This model represents the response from a guardrail enforcement operation,
    containing the processed text, any action taken, and raw response data.

    Attributes:
        text: The generated or processed text response from the guardrail.
        action: Optional action taken by the guardrail (e.g., "blocked", "modified", "allowed").
        raw: Optional raw response data from the underlying guardrail service.
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "use_enum_values": True,
        "validate_assignment": True,
        "validate_default": True,
    }

    text: str = Field(
        ...,
        description="Generated text response",
        min_length=0,
    )
    action: Action | None = Field(
        default=None,
        description="Action taken by the guardrail (e.g., 'blocked', 'modified', 'allowed')",
    )
    raw: Any | None = Field(
        default=None,
        description="Raw response data from the guardrail service",
        exclude=False,
    )
