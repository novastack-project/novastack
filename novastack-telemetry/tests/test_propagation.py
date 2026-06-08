from typing import Any

from novastack_telemetry._dispatcher_core import (
    _CONTEXT_METADATA_KEY,
    Dispatcher,
    _active_context_metadata,
    _DispatcherManager,
)
from novastack_telemetry.observability import BaseObservability


class PropagatingObservability(BaseObservability):
    """Unified handler that captures/restores a fake trace context."""

    def capture_propagation_context(self) -> dict[str, Any]:
        return {"test_handler": {"trace_id": "abc123", "span_id": "def456"}}

    def restore_propagation_context(self, context: dict[str, Any]) -> None:
        self._restored_context = context


def test_capture_propagation_context_basic():
    handler = PropagatingObservability()
    d = Dispatcher(handlers=[handler], propagate=False)

    ctx = d.capture_propagation_context()

    assert ctx["test_handler"]["trace_id"] == "abc123"
    assert ctx["test_handler"]["span_id"] == "def456"


def test_capture_includes_telemetry_tags():
    handler = BaseObservability()
    d = Dispatcher(handlers=[handler], propagate=False)

    token = _active_context_metadata.set({"user_id": "u1", "session": "s1"})
    try:
        ctx = d.capture_propagation_context()
    finally:
        _active_context_metadata.reset(token)

    assert ctx[_CONTEXT_METADATA_KEY] == {"user_id": "u1", "session": "s1"}


def test_capture_omits_telemetry_tags_when_empty():
    handler = BaseObservability()
    d = Dispatcher(handlers=[handler], propagate=False)

    ctx = d.capture_propagation_context()

    assert _CONTEXT_METADATA_KEY not in ctx


def test_restore_propagation_context_basic():
    handler = PropagatingObservability()
    d = Dispatcher(handlers=[handler], propagate=False)

    context = {"test_handler": {"trace_id": "abc123"}}
    d.restore_propagation_context(context)

    assert handler._restored_context == context


def test_restore_sets_telemetry_tags():
    handler = BaseObservability()
    d = Dispatcher(handlers=[handler], propagate=False)

    d.restore_propagation_context({_CONTEXT_METADATA_KEY: {"user_id": "u1"}})

    assert _active_context_metadata.get() == {"user_id": "u1"}

    _active_context_metadata.set({})


def test_capture_walks_parent_chain():
    parent_handler = PropagatingObservability()
    child_handler = BaseObservability()

    parent = Dispatcher(name="parent", handlers=[parent_handler], propagate=False)
    child = Dispatcher(
        name="child",
        handlers=[child_handler],
        propagate=True,
        parent_name="parent",
    )
    manager = _DispatcherManager(parent)
    manager.add_dispatcher(child)
    child.dispatcher_manager = manager
    parent.dispatcher_manager = manager

    ctx = child.capture_propagation_context()

    assert "test_handler" in ctx


def test_restore_walks_parent_chain():
    parent_handler = PropagatingObservability()
    child_handler = PropagatingObservability()

    parent = Dispatcher(name="parent", handlers=[parent_handler], propagate=False)
    child = Dispatcher(
        name="child",
        handlers=[child_handler],
        propagate=True,
        parent_name="parent",
    )
    manager = _DispatcherManager(parent)
    manager.add_dispatcher(child)
    child.dispatcher_manager = manager
    parent.dispatcher_manager = manager

    context = {"test_handler": {"trace_id": "xyz"}}
    child.restore_propagation_context(context)

    assert child_handler._restored_context == context
    assert parent_handler._restored_context == context


def test_capture_stops_at_propagate_false():
    parent_handler = PropagatingObservability()
    child_handler = BaseObservability()

    parent = Dispatcher(name="parent", handlers=[parent_handler], propagate=False)
    child = Dispatcher(
        name="child",
        handlers=[child_handler],
        propagate=False,
        parent_name="parent",
    )
    manager = _DispatcherManager(parent)
    manager.add_dispatcher(child)
    child.dispatcher_manager = manager
    parent.dispatcher_manager = manager

    ctx = child.capture_propagation_context()

    assert "test_handler" not in ctx


def test_roundtrip_capture_restore():
    """Capture from one dispatcher, restore on another — simulates cross-process."""
    source_handler = PropagatingObservability()
    source = Dispatcher(handlers=[source_handler], propagate=False)

    token = _active_context_metadata.set({"env": "prod"})
    try:
        ctx = source.capture_propagation_context()
    finally:
        _active_context_metadata.reset(token)

    dest_handler = PropagatingObservability()
    dest = Dispatcher(handlers=[dest_handler], propagate=False)

    dest.restore_propagation_context(ctx)

    assert dest_handler._restored_context == ctx
    assert _active_context_metadata.get() == {"env": "prod"}

    _active_context_metadata.set({})


def test_capture_swallows_handler_exceptions():
    class BrokenObservability(BaseObservability):
        def capture_propagation_context(self) -> dict[str, Any]:
            raise RuntimeError("boom")

    handler = BrokenObservability()
    d = Dispatcher(handlers=[handler], propagate=False)

    ctx = d.capture_propagation_context()
    assert isinstance(ctx, dict)


def test_restore_swallows_handler_exceptions():
    class BrokenObservability(BaseObservability):
        def restore_propagation_context(self, context: dict[str, Any]) -> None:
            raise RuntimeError("boom")

    handler = BrokenObservability()
    d = Dispatcher(handlers=[handler], propagate=False)

    d.restore_propagation_context({"some": "data"})
