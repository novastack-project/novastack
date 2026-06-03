from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class BaseSpan(BaseModel):
    """Abstract base class defining the interface for span models."""

    model_config = {"arbitrary_types_allowed": True}

    id_: str = Field(
        default_factory=lambda: str(uuid4()), description="The Id of span."
    )
    parent_id: str | None = Field(default=None, description="The Id of parent span.")
    metadata: dict[str, Any] = Field(default={})


class Span(BaseSpan):
    """Simple span class."""

    start_time: datetime = Field(default_factory=lambda: datetime.now())
    end_time: datetime | None = Field(default=None)
    duration: float = Field(default=0.0, description="Duration of span in seconds.")
