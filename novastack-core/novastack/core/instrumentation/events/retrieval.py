from novastack.core.document import DocumentWithScore
from novastack_instrumentation.events import BaseEvent


class RetrievalStartEvent(BaseEvent):
    """
    RetrievalStartEvent.

    Args:
        query: (str) The query string to search for similar documents.
        config_dict (dict): Retrieval model.
    """

    query: str
    config_dict: dict

    @classmethod
    def class_name(cls) -> str:
        return "RetrievalStartEvent"


class RetrievalEndEvent(BaseEvent):
    """
    RetrievalEndEvent.

    Args:
        documents (DocumentWithScore): List of documents with scores.
    """

    documents: DocumentWithScore

    @classmethod
    def class_name(cls) -> str:
        return "RetrievalEndEvent"
