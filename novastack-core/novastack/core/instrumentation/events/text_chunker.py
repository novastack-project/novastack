from donkey_instrumentation.events import BaseEvent
from novastack.core.document import Document


class TextChunkerStartEvent(BaseEvent):
    """
    TextChunkerStartEvent.

    Args:
        config_dict (dict): Text chunker model.
    """

    config_dict: dict

    @classmethod
    def class_name(cls) -> str:
        return "TextChunkerStartEvent"


class TextChunkerEndEvent(BaseEvent):
    """
    TextChunkerEndEvent.

    Args:
        chunks (list[Document] | list[str]): List of documents.
    """

    chunks: list[Document] | list[str]

    @classmethod
    def class_name(cls) -> str:
        return "TextChunkerEndEvent"
