from abc import abstractmethod

from novastack.core.bridge.pydantic import BaseModel
from novastack.core.document import Document


class BaseComponent(BaseModel):
    """Base component object."""

class TransformerComponent(BaseComponent):
    """Abstract base class for document transformer components."""

    @abstractmethod
    def __call__(self, documents: list[Document]) -> list[Document]:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the __call__() method."
        )
