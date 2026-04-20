import uuid
from abc import ABC, abstractmethod
from hashlib import sha256
from typing import Any

import numpy as np
from novastack.core.bridge.pydantic import (
    BaseModel,
    Field,
    computed_field,
    field_validator,
)


class BaseDocument(BaseModel, ABC):
    """Abstract base class defining the interface for retrievable documents."""

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True
    }

    id_: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique Id of the document.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="A flat dictionary of metadata fields.",
    )
    embedding: list[float] | np.ndarray | None = Field(
        default=None,
        description="Embedding of the document.",
    )

    @field_validator("metadata", mode="before")
    @classmethod
    def _validate_metadata(cls, v) -> dict:
        """Ensure metadata is always a dict."""
        if v is None:
            return {}
        return v

    @abstractmethod
    def get_content(self) -> str:
        """Get document content."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the get_content() method"
        )

    @property
    @abstractmethod
    def hash(self) -> str:
        """Get document hash."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the get_content() method"
        )


class Document(BaseDocument):
    """Generic interface for data document."""

    text: str = Field(default="", description="Text content of the document.")

    @classmethod
    def class_name(cls) -> str:
        return "Document"

    def get_content(self) -> str:
        """Get the text content."""
        return self.text

    @computed_field
    @property
    def hash(self) -> str:
        """Get document hash based on text content."""
        return str(sha256(str(self.text).encode("utf-8", "surrogatepass")).hexdigest())


class DocumentWithScore(BaseModel):
    """Document with associated relevance score."""

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True
    }

    document: BaseDocument
    score: float | None = Field(
        default=None,
        description="Relevance score for the document.",
    )

    @classmethod
    def class_name(cls) -> str:
        return "DocumentWithScore"

    @property
    def normalized_score(self) -> float:
        """Get normalized score (0.0 if None)."""
        return self.score if self.score is not None else 0.0

    # #### pass through properties to BaseDocument ####
    @property
    def id_(self) -> str:
        """Get document Id."""
        return self.document.id_

    @property
    def metadata(self) -> dict:
        """Get document metadata."""
        return self.document.metadata

    def get_content(self) -> str:
        """Get document content."""
        return self.document.get_content()
