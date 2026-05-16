from abc import ABC, abstractmethod

from novastack.core.bridge.pydantic import BaseModel, Field
from novastack.core.document import Document


class BaseLoader(BaseModel, ABC):
    """Abstract base class defining the interface for document loader."""

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
        "validate_assignment": True,
        "validate_default": True,
    }

    @classmethod
    def class_name(cls) -> str:
        """Returns the class name of the loader."""
        return "BaseLoader"

    @abstractmethod
    def load_data(self) -> list[Document]:
        """Loads data and returns a list of documents."""

class BaseFileLoader(BaseLoader):
    """
    Abstract base class defining the interface for file-based document loaders.

    Attributes:
        input_file (str): File path to load.
    """

    input_file: str = Field(...,
        description="File path to load",
    )

    @classmethod
    def class_name(cls) -> str:
        """Returns the class name of the loader."""
        return "BaseFileLoader"
