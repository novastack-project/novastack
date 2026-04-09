from abc import ABC, abstractmethod
from typing import Any

from novastack.core.bridge.pydantic import BaseModel, ConfigDict
from novastack.core.document import DocumentWithScore


class BaseRetriever(BaseModel, ABC):
    """
    Abstract base class for document retrievers.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    @abstractmethod
    def query_documents(
        self,
        query: str,
        **kwargs: Any,
    ) -> list[DocumentWithScore]:
        """
        Query and retrieve relevant documents.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the query_documents() method"
        )
