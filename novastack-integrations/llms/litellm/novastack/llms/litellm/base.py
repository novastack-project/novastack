from typing import Any

from novastack.core.bridge.pydantic import Field
from novastack.core.llms import BaseLLM, ChatMessage, ChatResponse, CompletionResponse
from novastack.core.llms.decorators import llm_chat_callback, llm_completion_callback

import litellm


class LiteLLM(BaseLLM):
    """
    A wrapper class for interacting with a LiteLLM-compatible large language model (LLM).
    For more information, see: [https://docs.litellm.ai/](https://docs.litellm.ai/).


    Attributes:
        model (str): The identifier of the LLM model to use (e.g., "gpt-4", "llama-3").
        temperature (float, optional): Sampling temperature to use. Must be between 0.0 and 1.0.
            Higher values result in more random outputs, while lower values make the
            output more deterministic. Default is 1.0.
        max_tokens (int, optional): The maximum number of tokens to generate in the completion.
        api_key (str): API key used for authenticating with the LLM provider.
        additional_kwargs (dict[str, Any], optional): A dictionary of additional parameters passed
            to the LLM during completion. This allows customization of the request beyond
            the standard parameters.
        callback_manager: (ModelMonitor, optional): The callback manager is used for observability.
    """

    model: str
    temperature: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="The temperature to use. Higher values make the output more random, "
        "while lower values make it more focused and deterministic.",
    )
    max_tokens: int = Field(ge=0)
    api_key: str
    additional_kwargs: dict[str, Any] = Field(default_factory=dict)

    def _get_all_kwargs(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **self.additional_kwargs,
            **kwargs,  # Method-provided kwargs override class-level kwargs
            "model": self.model,  # Always enforced from class
            "api_key": self.api_key,  # Always enforced from class
        }

    @llm_completion_callback()
    def completion(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        """
        Creates a completion for the provided prompt and parameters. Using OpenAI's standard endpoint (/completions).

        Args:
            prompt (str): The input prompt to generate a completion for.
            **kwargs (Any): Additional keyword arguments to customize the LLM completion request.
        """
        all_kwargs = self._get_all_kwargs(**kwargs)

        response = litellm.text_completion(prompt=prompt, **all_kwargs).model_dump(
            exclude_none=True
        )

        return CompletionResponse(
            text=response["choices"][0]["text"],
            input_token_count=response.get("usage", {}).get("prompt_tokens"),
            generated_token_count=response.get("usage", {}).get("completion_tokens"),
            raw=response,
        )

    @llm_chat_callback()
    def chat_completion(
        self, messages: list[ChatMessage | dict], **kwargs: Any
    ) -> ChatResponse:
        """
        Creates a chat completion for LLM. Using OpenAI's standard endpoint (/chat/completions).

        Args:
            messages (list[ChatMessage]): A list of chat messages as input for the LLM.
            **kwargs (Any): Additional keyword arguments to customize the LLM completion request.
        """
        all_kwargs = self._get_all_kwargs(**kwargs)
        input_messages_dict = [
            ChatMessage.model_validate(message).to_dict() for message in messages
        ]

        response = litellm.completion(
            messages=input_messages_dict, **all_kwargs
        ).model_dump(exclude_none=True)
        message_dict = response["choices"][0]["message"]

        return ChatResponse(
            message=ChatMessage(
                role=message_dict.get("role"), content=message_dict.get("content", None)
            ),
            raw=response,
        )
