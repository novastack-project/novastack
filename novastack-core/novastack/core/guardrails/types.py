from typing import Any

from novastack.core.bridge.pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


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

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
    )

    text: str = Field(
        ...,
        description="Generated text response",
        min_length=0,
    )
    action: str | None = Field(
        default=None,
        description="Action taken by the guardrail (e.g., 'blocked', 'modified', 'allowed')",
    )
    raw: Any | None = Field(
        default=None,
        description="Raw response data from the guardrail service",
        exclude=False,
    )

    @field_validator("action")
    @classmethod
    def _validate_action(cls, v: str | None) -> str | None:
        """Validate and normalize action field."""
        if v is not None and isinstance(v, str):
            v = v.strip().lower()
            if v == "":
                return None
        return v
