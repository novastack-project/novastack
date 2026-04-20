from abc import ABC, abstractmethod
from typing import Any

from novastack.core.bridge.pydantic import BaseModel, Field, field_validator


class BaseEvaluator(BaseModel, ABC):
    """
    Abstract base class defining the interface for evaluation metrics.

    All evaluators should inherit from this class and implement the evaluate method.
    """

    model_config = {
        "arbitrary_types_allowed": True,
        "use_enum_values": True,
        "validate_assignment": True,
        "validate_default": True,
    }

    score_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum required score for evaluation approval",
    )

    @field_validator("score_threshold")
    @classmethod
    def _validate_threshold(cls, v: float) -> float:
        """Validate that threshold is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"score_threshold must be between 0.0 and 1.0, got: {v}")
        return v

    @classmethod
    def class_name(cls) -> str:
        return "BaseEvaluator"

    @abstractmethod
    def evaluate(
        self,
        query: str | None = None,
        generated_text: str | None = None,
        contexts: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        """
        Evaluate the given inputs and return evaluation results.

        This method should be implemented by all concrete evaluator classes.
        The specific parameters will vary depending on the evaluation type.

        Returns:
            dict: Dictionary containing evaluation results. Should include at minimum:
                - score (float): The evaluation score
                - passing (bool): Whether the evaluation passed a threshold
                Additional keys can be included for specific evaluation details.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the evaluate() method"
        )
