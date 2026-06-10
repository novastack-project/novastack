from abc import abstractmethod

from novastack.core.component import TransformerComponent
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

    @dispatcher.span
    def get_text_chunks(self, text: str) -> list[str]:
        """
        Split a single string of text into smaller chunks.

        Args:
            text (str): Input text to split.
        """
        config_dict = self.model_dump(exclude={"api_key"})
        dispatcher.event(
            TextChunkerStartEvent(
                config_dict=config_dict,
            )
        )

        chunks = self._get_text_chunks(text)

        dispatcher.event(
            TextChunkerEndEvent(
                chunks=chunks,
            )
        )
        return chunks

    @dispatcher.span
    def get_document_chunks(self, documents: list[Document]) -> list[Document]:
        """
        Split a list of documents into smaller document chunks.

        Args:
            documents (list[Document]): Documents to split.
        """
        config_dict = self.model_dump(exclude={"api_key"})
        dispatcher.event(
            TextChunkerStartEvent(
                config_dict=config_dict,
            )
        )
        documents = []

        for document in documents:
            texts = self._get_text_chunks(document.get_content())
            metadata = {**document.metadata}

            for text in texts:
                if len(texts) > 1:
                    metadata["ref_doc_id"] = document.id_
                    metadata["ref_doc_hash"] = document.hash

                documents.append(
                    Document(
                        text=text,
                        metadata=metadata,
                    ),
                )

        dispatcher.event(
            TextChunkerEndEvent(
                chunks=documents,
            )
        )
        return documents

    def __call__(self, documents: list[Document]) -> list[Document]:
        return self.get_document_chunks(documents)
