from typing import Any

from novastack.core.bridge.pydantic import Field
from novastack.core.llms import BaseLLM, ChatMessage, ChatResponse, CompletionResponse
from novastack.core.llms.decorators import llm_chat_callback, llm_completion_callback
from novastack.llms.watsonx.supporting_classes.enums import Region


class WatsonxLLM(BaseLLM):
    """
    A wrapper class for interacting with a IBM watsonx.ai large language models (LLMs).
    For more information, see [here](https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/fm-models.html?context=wx&audience=wdp).


    Attributes:
        model (str): The identifier of the LLM model to use (e.g., "openai/gpt-oss-120b", "meta-llama/llama-3-3-70b-instruct").
        api_key (str): API key used for authenticating with the LLM provider.
        region (Region, optional): The region where watsonx.ai is hosted when using IBM Cloud.
            Defaults to `us-south`.
        project_id (str, optional): The project ID in watsonx.ai.
        space_id (str, optional): The space ID in watsonx.ai.
        additional_kwargs (dict[str, Any], optional): A dictionary of additional parameters passed
            to the LLM during completion. This allows customization of the request beyond
            the standard parameters.
        callback_manager: (PromptMonitor, optional): The callback manager is used for observability.
    """

    model: str
    api_key: str
    region: Region | str = Region.US_SOUTH
    project_id: str = Field(default=None)
    space_id: str = Field(default=None)
    params: dict[str, Any] = Field(default_factory=dict)
    additional_kwargs: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context):  # noqa: PYI063
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        self.region = Region.from_value(self.region)

        if (not (self.project_id or self.space_id)) or (
            self.project_id and self.space_id
        ):
            raise ValueError(
                "Invalid configuration: 'project_id' or 'space_id' must be provided. Not both."
            )

        self._model_inference = ModelInference(
            **self.additional_kwargs,
            model_id=self.model,
            credentials=Credentials(
                api_key=self.api_key,
                url=self.region.watsonxai,
            ),
            project_id=self.project_id,
            space_id=self.space_id,
        )

    @llm_completion_callback()
    def completion(
        self,
        prompt: str,
        guardrails: bool = False,
        params: dict[str, Any] = {},
        **kwargs: Any,
    ) -> CompletionResponse:
        """
        Creates a completion for the provided prompt and parameters. Using OpenAI's standard endpoint (/completions).

        Args:
            prompt (str): The input prompt to generate a completion for.
            guardrails (bool, optional): The detection filter for potentially hateful, abusive, and/or profane language (HAP).
            params (dict, optional): MetaProps for text generation. Method-provided params override class-level params.
            **kwargs (Any, optional): Additional keyword arguments to customize the LLM completion request.
        """
        response = self._model_inference.generate(
            **kwargs,
            prompt=prompt,
            guardrails=guardrails,
            params={**self.params, **params},
        )

        return CompletionResponse(
            text=response["results"][0].get("generated_text"),
            input_token_count=response["results"][0].get("input_token_count"),
            generated_token_count=response["results"][0].get("generated_token_count"),
            raw=response,
        )

    @llm_chat_callback()
    def chat_completion(
        self,
        messages: list[ChatMessage | dict],
        params: dict[str, Any] = {},
        **kwargs: Any,
    ) -> ChatResponse:
        """
        Creates a chat completion for LLM. Using OpenAI's standard endpoint (/chat/completions).

        Args:
            messages (list[ChatMessage]): A list of chat messages as input for the LLM.
            params (dict, optional): MetaProps for text generation. Method-provided params override class-level params.
            **kwargs (Any, optional): Additional keyword arguments to customize the LLM completion request.
        """
        input_messages_dict = [
            ChatMessage.from_value(message).to_dict() for message in messages
        ]

        response = self._model_inference.chat(
            **kwargs,
            messages=input_messages_dict,
            params={**self.params, **params},
        )
        message_dict = response["choices"][0]["message"]

        return ChatResponse(
            message=ChatMessage(
                role=message_dict.get("role"), content=message_dict.get("content", None)
            ),
            raw=response,
        )
