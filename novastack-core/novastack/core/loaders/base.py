from abc import ABC, abstractmethod
from typing import Any

from novastack.core.bridge.pydantic import BaseModel
from novastack.core.document import Document


class BaseLoader(BaseModel, ABC):
    """Abstract base class defining the interface for document loader."""

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
        "extra":"forbid",
    }

    @classmethod
    def class_name(cls) -> str:
        """Returns the class name of the loader."""
        return "BaseLoader"

    @abstractmethod
    def load_data(self, input_dir: str, **kwargs: Any) -> list[Document]:
        """
        Loads data and returns a list of documents.

        Args:
            input_dir (str): Directory path from which to load the documents.

        Returns:
            list[Document]: A list of loaded documents.
        """
