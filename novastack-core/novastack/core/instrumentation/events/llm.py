from novastack.core.llms import ChatMessage, ChatResponse, CompletionResponse
from novastack_instrumentation.events import BaseEvent


class LLMCompletionStartEvent(BaseEvent):
    """
    LLMCompletionStartEvent.

    Args:
        prompt: (str) The input prompt to generate a completion for.
        config_dict (dict): LLM model.
    """

    prompt: str
    config_dict: dict

    @classmethod
    def class_name(cls) -> str:
        return "LLMCompletionStartEvent"


class LLMCompletionEndEvent(BaseEvent):
    """
    LLMCompletionEndEvent.

    Args:
        response (CompletionResponse): Completion for response.
    """

    response: CompletionResponse

    @classmethod
    def class_name(cls) -> str:
        return "LLMCompletionEndEvent"


class LLMChatStartEvent(BaseEvent):
    """
    LLMChatStartEvent.

    Args:
        messages: (list[ChatMessage]): List of messages.
        config_dict (dict): LLM model.
    """

    messages: list[ChatMessage]
    config_dict: dict

    @classmethod
    def class_name(cls) -> str:
        return "LLMChatStartEvent"


class LLMChatEndEvent(BaseEvent):
    """
    LLMChatEndEvent.

    Args:
        response (ChatResponse): Chat completion for response.
    """

    response: ChatResponse

    @classmethod
    def class_name(cls) -> str:
        return "LLMChatEndEvent"
