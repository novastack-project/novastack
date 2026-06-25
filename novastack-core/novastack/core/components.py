import json
from abc import abstractmethod
from typing import Any

from novastack.core.bridge.pydantic import BaseModel
from novastack.core.document import Document


class BaseComponent(BaseModel):
    """Base component object."""

    @classmethod
    def class_name(cls) -> str:
        """Return the class name for identification purposes."""
        return "BaseComponent"

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        data = self.model_dump(**kwargs)
        data["class_name"] = self.class_name()
        return data

    def to_json(self, **kwargs: Any) -> str:
        data = self.to_dict(**kwargs)
        return json.dumps(data)


class TransformerComponent(BaseComponent):
    """Abstract base class for document transformer components."""

    @abstractmethod
    def __call__(self, documents: list[Document]) -> list[Document]:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the __call__() method."
        )
