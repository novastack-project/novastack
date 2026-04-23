from abc import ABC, abstractmethod

from novastack.core.bridge.pydantic import BaseModel, Field, model_validator
from novastack.core.observability.types import PayloadRecord
from novastack.core.prompts import PromptTemplate


class BaseObservability(BaseModel, ABC):
    """Abstract base class defining the interface for observability."""

    @classmethod
    def class_name(cls) -> str:
        return "BaseObservability"


class PromptObservability(BaseObservability):
    """
    Abstract base class for prompt observability with Pydantic validation.

    Attributes:
        prompt_template: Template for formatting prompts
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
        "validate_default": True,
    }

    prompt_template: PromptTemplate | None = Field(
        default=None, description="Template for formatting prompts"
    )

    input_field_name: str = Field(
        default="input_text", description="Column name used to store input message content into a structured format. Defaults to 'input_text'."
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_prompt_template(cls, data):
        if isinstance(data, dict) and "prompt_template" in data:
            data["prompt_template"] = PromptTemplate.model_validate_input(
                data["prompt_template"]
            )
        return data

    @classmethod
    def class_name(cls) -> str:
        return "PromptObservability"

    @abstractmethod
    def __call__(self, payload: PayloadRecord) -> None:
        """Process observability payload."""
