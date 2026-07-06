import inspect
import threading
from typing import Any, Optional

from pydantic import BaseModel, Field, PrivateAttr

from novastack_instrumentation.events.base import BaseEvent
from novastack_instrumentation.span.base import Span


class BaseObservability(BaseModel):
    """
    Unified observability that can handle events and spans.

    This is the foundation for moving toward to observability.
    BaseObservability can implement event handling and span handling.
    """

    model_config = {"arbitrary_types_allowed": True}

    open_spans: dict[str, Span] = Field(
        default_factory=dict, description="Dictionary of open spans."
    )
    completed_spans: list[Span] = Field(
        default_factory=list, description="List of completed spans."
    )
    dropped_spans: list[Span] = Field(
        default_factory=list, description="List of dropped spans."
    )
    events: list[BaseEvent] = Field(default_factory=list, description="List of events.")
    _lock: Optional[threading.Lock] = PrivateAttr(default=None)

    @property
    def lock(self) -> threading.Lock:
        if self._lock is None:
            self._lock = threading.Lock()
        return self._lock

    @classmethod
    def class_name(cls) -> str:
        return "BaseObservability"

    def on_event(self, event: BaseEvent, **kwargs: Any) -> Any:
        """Handle an event."""

    def on_span_start(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        parent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle span start."""

    def on_span_end(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        result: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle span end."""

    def on_span_exception(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        err: BaseException | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle span exception."""

    def shutdown(self) -> None:
        """Optional cleanup hook called during dispatcher shutdown."""
