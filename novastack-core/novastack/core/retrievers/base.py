from abc import abstractmethod
from typing import Any

from novastack.core.bridge.pydantic import BaseModel
from novastack.core.document import DocumentWithScore
from novastack.core.telemetry import DispatcherSpanMixin, get_dispatcher
from novastack.core.telemetry.events.retrieval import (
    RetrievalEndEvent,
    RetrievalStartEvent,
)

dispatcher = get_dispatcher(__name__)


class BaseRetriever(BaseModel, DispatcherSpanMixin):
    """
    Abstract base class for document retrievers.
    """

    model_config = {"arbitrary_types_allowed": True}

    @abstractmethod
    def _query_documents(
        self,
        query: str,
        **kwargs: Any,
    ) -> list[DocumentWithScore]:
        """
        Query and retrieve relevant documents.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the _query_documents() method"
        )

    @dispatcher.span
    def query_documents(
        self,
        query: str,
        **kwargs: Any,
    ) -> list[DocumentWithScore]:
        """
        Query and retrieve relevant documents.
        """
        config_dict = self.model_dump(exclude={"api_key"})
        dispatcher.event(
            RetrievalStartEvent(
                query=query,
                config_dict=config_dict,
            )
        )

        documents = self._query_documents(query, **kwargs)

        dispatcher.event(
            RetrievalEndEvent(
                documents=documents,
            )
        )
        return documents
