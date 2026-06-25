from abc import ABC, abstractmethod

from novastack.core.components import BaseComponent
from novastack.core.guardrails.schemas import GuardrailResponse


class BaseGuardrail(BaseComponent, ABC):
    """
    Abstract base class defining the interface for guardrails.

    This class provides the foundation for implementing guardrail systems
    that can validate and enforce policies on text inputs and outputs.
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
        "validate_default": True,
    }

    @classmethod
    def class_name(cls) -> str:
        return "BaseGuardrail"

    @abstractmethod
    def enforce(self, text: str, direction: str, **kwargs) -> GuardrailResponse:
        """Run policy enforcement on the specified text."""
