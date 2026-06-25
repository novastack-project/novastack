from abc import abstractmethod
from typing import Any

from novastack.core.bridge.pydantic import Field
from novastack.core.components import BaseComponent
from novastack.core.instrumentation import DispatcherSpanMixin, get_dispatcher
from novastack.core.instrumentation.events.llm import (
    LLMChatEndEvent,
    LLMChatStartEvent,
    LLMCompletionEndEvent,
    LLMCompletionStartEvent,
)
from novastack.core.llms.schemas import ChatMessage, ChatResponse, CompletionResponse
from novastack.core.observability import BaseObservability

dispatcher = get_dispatcher(__name__)


class BaseLLM(BaseComponent, DispatcherSpanMixin):
    """Abstract base class defining the interface for LLMs."""

    model_config = {
        "arbitrary_types_allowed": True,
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

    @abstractmethod
    def _completion(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """Generates a completion for LLM."""

    @abstractmethod
    def _chat_completion(
        self, messages: list[ChatMessage | dict], **kwargs: Any
    ) -> ChatResponse:
        """Generates a chat completion for LLM."""

    @dispatcher.span
    def completion(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """
        Creates a completion for the provided prompt and parameters. Using OpenAI's standard endpoint (/completions).

        Args:
            prompt (str): The input prompt to generate a completion for.
            **kwargs (Any): Additional keyword arguments to customize the LLM completion request.
        """
        config_dict = self.to_dict(exclude={"api_key"})
        dispatcher.event(
            LLMCompletionStartEvent(
                prompt=prompt,
                config_dict=config_dict,
            )
        )

        response = self._completion(prompt)

        dispatcher.event(
            LLMCompletionEndEvent(
                response=response,
            )
        )
        return response

    @dispatcher.span
    def chat_completion(
        self, messages: list[ChatMessage | dict], **kwargs: Any
    ) -> ChatResponse:
        """
        Creates a chat completion for LLM. Using OpenAI's standard endpoint (/chat/completions).

        Args:
            messages (list[ChatMessage]): A list of chat messages as input for the LLM.
            **kwargs (Any): Additional keyword arguments to customize the LLM completion request.
        """
        config_dict = self.to_dict(exclude={"api_key"})
        dispatcher.event(
            LLMChatStartEvent(
                messages=messages,
                config_dict=config_dict,
            )
        )

        response = self._chat_completion(messages)

        dispatcher.event(
            LLMChatEndEvent(
                response=response,
            )
        )
        return response

    def text_completion(self, prompt: str, **kwargs: Any) -> str:
        """
        Generates a chat completion for LLM. Using OpenAI's standard endpoint (/completions).

        Args:
            prompt (str): The input prompt to generate a completion for.
            **kwargs (Any): Additional keyword arguments to customize the LLM completion request.
        """
        response = self.completion(prompt=prompt, **kwargs)

        return response.text
