import inspect
from typing import Any

from novastack_instrumentation.dispatcher import Dispatcher
from novastack_instrumentation.events import BaseEvent
from novastack_instrumentation.observability import BaseObservability
from pydantic import Field


class UnifiedTestEvent(BaseEvent):
    message: str = "test"


class UnifiedTestHandler(BaseObservability):
    """A unified handler that handles both events and spans."""

    events: list[BaseEvent] = Field(default_factory=list)
    span_enters: list[str] = Field(default_factory=list)
    span_exits: list[str] = Field(default_factory=list)
    span_drops: list[str] = Field(default_factory=list)

    def on_event(self, event: BaseEvent, **kwargs: Any) -> Any:
        """Handle events."""
        self.events.append(event)

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
        self.span_enters.append(id_)

    def on_span_end(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        result: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle span exit."""
        self.span_exits.append(id_)

    def on_span_exception(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        err: BaseException | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle span exception."""
        self.span_drops.append(id_)


def test_unified_handler_receives_events():
    """Test that unified handlers receive events."""
    handler = UnifiedTestHandler()
    dispatcher = Dispatcher(handlers=[handler], propagate=False)

    event = UnifiedTestEvent(message="hello")
    dispatcher.event(event)

    assert len(handler.events) == 1
    assert handler.events[0].message == "hello"


def test_unified_handler_receives_spans():
    """Test that unified handlers receive span signals."""
    handler = UnifiedTestHandler()
    dispatcher = Dispatcher(handlers=[handler], propagate=False)

    @dispatcher.span
    def test_func():
        return "result"

    result = test_func()

    assert result == "result"
    assert len(handler.span_enters) == 1
    assert len(handler.span_exits) == 1
    assert len(handler.span_drops) == 0


def test_unified_handler_receives_span_drops():
    """Test that unified handlers receive span drop signals."""
    handler = UnifiedTestHandler()
    dispatcher = Dispatcher(handlers=[handler], propagate=False)

    @dispatcher.span
    def test_func_error():
        raise ValueError("test error")

    try:
        test_func_error()
    except ValueError:
        pass

    assert len(handler.span_enters) == 1
    assert len(handler.span_exits) == 0
    assert len(handler.span_drops) == 1
