from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from novastack_telemetry.span import _active_span_id


class BaseEvent(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    id_: str = Field(default_factory=lambda: str(uuid4()))
    span_id: str | None = Field(default_factory=_active_span_id.get)
    metadata: dict[str, Any] = Field(default={})

    @classmethod
    def class_name(cls) -> str:
        return "BaseEvent"


class SpanExceptionEvent(BaseEvent):
    """SpanExceptionEvent."""

    err_str: str

    @classmethod
    def class_name(cls) -> str:
        return "SpanExceptionEvent"
