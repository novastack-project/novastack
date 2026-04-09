from abc import ABC, abstractmethod

from novastack.core.bridge.pydantic import BaseModel, ConfigDict
from novastack.core.guardrails.types import GuardrailResponse


class BaseGuardrail(BaseModel, ABC):
    """
    Abstract base class defining the interface for guardrails.

    This class provides the foundation for implementing guardrail systems
    that can validate and enforce policies on text inputs and outputs.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    @classmethod
    def class_name(cls) -> str:
        return "BaseGuardrail"

    @abstractmethod
    def enforce(self, text: str, direction: str) -> GuardrailResponse:
        """Run policy enforcement on the specified text."""
