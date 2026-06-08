from novastack.core.document import Document
from novastack_telemetry.events import BaseEvent


class LoaderStartEvent(BaseEvent):
    """
    LoaderStartEvent.

    Args:
        config_dict (dict): Retrieval model.
    """

    config_dict: dict

    @classmethod
    def class_name(cls) -> str:
        return "LoaderStartEvent"


class LoaderEndEvent(BaseEvent):
    """
    LoaderEndEvent.

    Args:
        documents (Document): List of documents.
    """

    documents: Document

    @classmethod
    def class_name(cls) -> str:
        return "LoaderEndEvent"
