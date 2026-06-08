from abc import abstractmethod

from novastack.core.base.schema import TransformerComponent
from novastack.core.document import Document
from novastack.core.telemetry import DispatcherSpanMixin, get_dispatcher
from novastack.core.telemetry.events.text_chunker import (
    TextChunkerEndEvent,
    TextChunkerStartEvent,
)

dispatcher = get_dispatcher(__name__)


class BaseTextChunker(TransformerComponent, DispatcherSpanMixin):
    """Abstract base class defining the interface for text chunker."""

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
        "validate_default": True,
    }

    @classmethod
    def class_name(cls) -> str:
        return "BaseTextChunker"

    @abstractmethod
    def _get_text_chunks(self, text: str) -> list[str]:
        """Split a single string of text into smaller chunks."""

    @abstractmethod
    def _get_document_chunks(self, documents: list[Document]) -> list[Document]:
        """Split a list of documents into smaller document chunks."""

    @dispatcher.span
    def get_text_chunks(self, text: str) -> list[str]:
        """Split a single string of text into smaller chunks."""
        config_dict = self.model_dump(exclude={"api_key"})
        dispatcher.event(
            TextChunkerStartEvent(
                config_dict=config_dict,
            )
        )

        chunks = self._chunk_text(text)

        dispatcher.event(
            TextChunkerEndEvent(
                chunks=chunks,
            )
        )
        return chunks

    @dispatcher.span
    def get_document_chunks(self, documents: list[Document]) -> list[Document]:
        """Split a list of documents into smaller document chunks."""
        config_dict = self.model_dump(exclude={"api_key"})
        dispatcher.event(
            TextChunkerStartEvent(
                config_dict=config_dict,
            )
        )

        documents = self._chunk_documents(documents)

        dispatcher.event(
            TextChunkerEndEvent(
                chunks=documents,
            )
        )
        return documents

    def __call__(self, documents: list[Document]) -> list[Document]:
        return self.get_document_chunks(documents)
