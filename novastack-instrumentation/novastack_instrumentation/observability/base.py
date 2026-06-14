import inspect
from typing import Any

from pydantic import BaseModel

from novastack_instrumentation.events.base import BaseEvent


class BaseObservability(BaseModel):
    """
    Unified observability that can handle events and spans.

    This is the foundation for moving toward to observability.
    BaseObservability can implement event handling and span handling.
    """

    model_config = {"arbitrary_types_allowed": True}

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
