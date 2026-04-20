from abc import ABC, abstractmethod
from typing import Any

from novastack.core.bridge.pydantic import BaseModel, Field
from novastack.core.llms.types import ChatMessage, ChatResponse, CompletionResponse
from novastack.core.observability import BaseObservability


class BaseLLM(BaseModel, ABC):
    """Abstract base class defining the interface for LLMs."""

    model_config = {
        "arbitrary_types_allowed": True,
        "use_enum_values": True,
        "validate_assignment": True,
        "validate_default": True,
    }

    model: str = Field(
        ..., min_length=1, description="Name or identifier of the LLM model to use"
    )
    callback_manager: BaseObservability | None = Field(
        default=None,
        description="Optional observability callback manager for tracking LLM interactions",
    )

    @classmethod
    def class_name(cls) -> str:
        return "BaseLLM"

    def text_completion(self, prompt: str, **kwargs: Any) -> str:
        """
        Generates a chat completion for LLM. Using OpenAI's standard endpoint (/completions).

        Args:
            prompt (str): The input prompt to generate a completion for.
            **kwargs (Any): Additional keyword arguments to customize the LLM completion request.
        """
        response = self.completion(prompt=prompt, **kwargs)

        return response.text

    @abstractmethod
    def completion(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Generates a completion for LLM."""

    @abstractmethod
    def chat_completion(
        self, messages: list[ChatMessage | dict], **kwargs: Any
    ) -> ChatResponse:
        """Generates a chat completion for LLM."""
