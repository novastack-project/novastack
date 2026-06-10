from novastack_instrumentation.events import BaseEvent


class EmbeddingStartEvent(BaseEvent):
    """
    EmbeddingStartEvent.

    Args:
        config_dict (dict): Embedding model.
    """

    config_dict: dict

    @classmethod
    def class_name(cls) -> str:
        return "EmbeddingStartEvent"


class EmbeddingEndEvent(BaseEvent):
    """
    EmbeddingEndEvent.

    Args:
        embeddings (List[List[float]]): List of embeddings.
    """

    embeddings: list[list[float]]

    @classmethod
    def class_name(cls) -> str:
        return "EmbeddingEndEvent"
