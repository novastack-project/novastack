from abc import ABC, abstractmethod

from novastack.core.bridge.pydantic import BaseModel
from novastack.core.document import Document, DocumentWithScore


class BaseVectorStore(BaseModel, ABC):
    """
    Abstract base class defining the interface for vector store.
    """

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def class_name(cls) -> str:
        """Return the class name for identification purposes."""
        return "BaseVectorStore"

    @abstractmethod
    def add_documents(self, documents: list[Document]) -> list[str]:
        """
        Add documents to vector store.

        Args:
            documents: List of documents to add to the vector store.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the add_documents() method"
        )

    @abstractmethod
    def query_documents(self, query: str, top_k: int = 4) -> list[DocumentWithScore]:
        """
        Query for similar documents in the vector store based on the input query provided.

        Args:
            query: The query string to search for similar documents.
            top_k: Number of top results to return. Defaults to 4.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the query_documents() method"
        )

    @abstractmethod
    def delete_documents(self, ids: list[str]) -> None:
        """
        Delete documents from vector store.

        Args:
            ids: List of document IDs to delete from the vector store.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the delete_documents() method"
        )

    @abstractmethod
    def get_all_documents(self, include_fields: list[str] = []) -> list[Document]:
        """
        Get all documents from vector store.

        Args:
            include_fields: Optional list of fields to include in the response.
                          If empty, all fields are included.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the get_all_documents() method"
        )

    def get_all_document_hashes(self) -> tuple[list[str], list[str], list[str]]:
        """
        Get all document IDs and hashes from vector store.

        This is a utility method that retrieves document identifiers and their
        content hashes for deduplication and synchronization purposes.
        """
        hits = self.get_all_documents()

        ids = [doc.id_ for doc in hits]
        hashes = [doc.metadata.get("hash", "") for doc in hits]
        ref_hashes = [doc.metadata.get("ref_doc_hash", "") for doc in hits]

        return ids, hashes, ref_hashes
