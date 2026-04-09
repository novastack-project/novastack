from abc import ABC, abstractmethod

from novastack.core.document import Document


class TransformerComponent(ABC):
    """
    Abstract base class for document transformer components.
    """

    @abstractmethod
    def __call__(self, documents: list[Document]) -> list[Document]:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the __call__() method"
        )
