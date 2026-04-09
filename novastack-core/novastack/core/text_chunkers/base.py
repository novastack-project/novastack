from abc import ABC, abstractmethod

from novastack.core.bridge.pydantic import BaseModel, ConfigDict
from novastack.core.document import Document
from novastack.core.schema import TransformerComponent


class BaseTextChunker(BaseModel, TransformerComponent, ABC):
    """Abstract base class defining the interface for text chunker."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    @classmethod
    def class_name(cls) -> str:
        return "BaseTextChunker"

    @abstractmethod
    def chunk_text(self, text: str) -> list[str]:
        """Split a single string of text into smaller chunks."""

    @abstractmethod
    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        """Split a list of documents into smaller document chunks."""

    def __call__(self, documents: list[Document]) -> list[Document]:
        return self.chunk_documents(documents)
