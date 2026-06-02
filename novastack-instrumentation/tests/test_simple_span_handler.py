import pytest
from novastack_instrumentation._dispatcher_core import Dispatcher
from novastack_instrumentation.events import BaseEvent
from novastack_instrumentation.observability.novastack_debug import (
    NovastackDebugObservability,
)


class SampleEvent(BaseEvent):
    message: str = "test"

    @classmethod
    def class_name(cls) -> str:
        return "SampleEvent"


def test_simple_span_callback_basic():
    """Test basic span tracking with NovastackDebugObservability."""
    handler = NovastackDebugObservability()
    dispatcher = Dispatcher(callbacks=[handler], propagate=False)

    @dispatcher.span
    def parent_func():
        child_func()
        return "parent_result"

    @dispatcher.span
    def child_func():
        return "child_result"

    result = parent_func()

    assert result == "parent_result"
    assert len(handler.completed_spans) == 2
    assert len(handler.open_spans) == 0
    assert len(handler.dropped_spans) == 0


def test_simple_span_callback_tracks_events():
    """Test that NovastackDebugObservability tracks events."""
    handler = NovastackDebugObservability()
    dispatcher = Dispatcher(callbacks=[handler], propagate=False)

    @dispatcher.span
    def test_func():
        dispatcher.event(SampleEvent(message="event1"))
        dispatcher.event(SampleEvent(message="event2"))
        return "result"

    test_func()

    assert len(handler.completed_spans) == 1
    assert len(handler.events) == 2
    assert handler.events[0].message == "event1"
    assert handler.events[1].message == "event2"


def test_simple_span_callback_with_error():
    """Test span tracking when errors occur."""
    handler = NovastackDebugObservability()
    dispatcher = Dispatcher(callbacks=[handler], propagate=False)

    @dispatcher.span
    def error_func():
        raise ValueError("test error")

    with pytest.raises(ValueError):
        error_func()

    assert len(handler.completed_spans) == 0
    assert len(handler.open_spans) == 0
    assert len(handler.dropped_spans) == 1


def test_print_trace_trees_basic():
    """Test print_trace_trees with basic hierarchy."""
    handler = NovastackDebugObservability()
    dispatcher = Dispatcher(callbacks=[handler], propagate=False)

    @dispatcher.span
    def parent_func():
        child_func()
        return "parent_result"

    @dispatcher.span
    def child_func():
        return "child_result"

    parent_func()

    try:
        handler.print_trace_trees()
    except ImportError:
        pytest.skip("treelib not installed")


def test_print_trace_trees_with_events():
    """Test print_trace_trees displays events under spans."""
    handler = NovastackDebugObservability()
    dispatcher = Dispatcher(callbacks=[handler], propagate=False)

    @dispatcher.span
    def parent_func():
        dispatcher.event(SampleEvent(message="parent_event"))
        child_func()
        return "parent_result"

    @dispatcher.span
    def child_func():
        dispatcher.event(SampleEvent(message="child_event"))
        return "child_result"

    parent_func()

    assert len(handler.events) == 2
    assert len(handler.completed_spans) == 2

    parent_span = next(s for s in handler.completed_spans if "parent_func" in s.id_)
    child_span = next(s for s in handler.completed_spans if "child_func" in s.id_)

    parent_events = [e for e in handler.events if e.span_id == parent_span.id_]
    child_events = [e for e in handler.events if e.span_id == child_span.id_]

    assert len(parent_events) == 1
    assert len(child_events) == 1
    assert parent_events[0].message == "parent_event"
    assert child_events[0].message == "child_event"

    try:
        trees = handler._get_trace_trees()
        assert len(trees) > 0

        tree = trees[0]
        all_nodes = tree.all_nodes()
        event_nodes = [n for n in all_nodes if "SampleEvent" in n.tag]
        assert len(event_nodes) == 2
    except ImportError:
        pytest.skip("treelib not installed")


def test_print_trace_trees_multiple_roots():
    """Test print_trace_trees with multiple root spans."""
    handler = NovastackDebugObservability()
    dispatcher = Dispatcher(callbacks=[handler], propagate=False)

    @dispatcher.span
    def func1():
        return "result1"

    @dispatcher.span
    def func2():
        return "result2"

    func1()
    func2()

    assert len(handler.completed_spans) == 2

    try:
        handler.print_trace_trees()
    except ImportError:
        pytest.skip("treelib not installed")


def test_print_trace_trees_nested():
    """Test print_trace_trees with deeply nested spans."""
    handler = NovastackDebugObservability()
    dispatcher = Dispatcher(callbacks=[handler], propagate=False)

    @dispatcher.span
    def level1():
        level2()
        return "level1"

    @dispatcher.span
    def level2():
        level3()
        return "level2"

    @dispatcher.span
    def level3():
        return "level3"

    level1()

    assert len(handler.completed_spans) == 3

    try:
        handler.print_trace_trees()
    except ImportError:
        pytest.skip("treelib not installed")


def test_get_trace_trees_returns_trees():
    """Test that _get_trace_trees returns Tree objects."""
    handler = NovastackDebugObservability()
    dispatcher = Dispatcher(callbacks=[handler], propagate=False)

    @dispatcher.span
    def test_func():
        return "result"

    test_func()

    try:
        trees = handler._get_trace_trees()
        assert len(trees) > 0

        from treelib.tree import Tree

        assert all(isinstance(t, Tree) for t in trees)
    except ImportError:
        pytest.skip("treelib not installed")


def test_span_callback_parent_child_relationship():
    """Test that parent-child relationships are correctly tracked."""
    handler = NovastackDebugObservability()
    dispatcher = Dispatcher(callbacks=[handler], propagate=False)

    @dispatcher.span
    def parent_func():
        child_func()
        return "parent"

    @dispatcher.span
    def child_func():
        return "child"

    parent_func()

    assert len(handler.completed_spans) == 2

    root_spans = [s for s in handler.completed_spans if s.parent_id is None]
    child_spans = [s for s in handler.completed_spans if s.parent_id is not None]

    assert len(root_spans) == 1
    assert len(child_spans) == 1

    parent_span = root_spans[0]
    child_span = child_spans[0]

    assert child_span.parent_id == parent_span.id_


def test_print_event_trees():
    """Test print_event_trees displays events grouped by span."""
    handler = NovastackDebugObservability()
    dispatcher = Dispatcher(callbacks=[handler], propagate=False)

    @dispatcher.span
    def test_func():
        dispatcher.event(SampleEvent(message="event1"))
        dispatcher.event(SampleEvent(message="event2"))
        return "result"

    test_func()

    try:
        handler.print_event_trees()
        trees = handler._get_event_trees()
        assert len(trees) == 1

        tree = trees[0]
        all_nodes = tree.all_nodes()

        assert len(all_nodes) == 3
    except ImportError:
        pytest.skip("treelib not installed")


def test_print_trace_trees_spans_only():
    """Test print_trace_trees with include_events=False."""
    handler = NovastackDebugObservability()
    dispatcher = Dispatcher(callbacks=[handler], propagate=False)

    @dispatcher.span
    def parent_func():
        dispatcher.event(SampleEvent(message="parent_event"))
        child_func()
        return "parent_result"

    @dispatcher.span
    def child_func():
        dispatcher.event(SampleEvent(message="child_event"))
        return "child_result"

    parent_func()

    assert len(handler.events) == 2

    try:
        trees = handler._get_trace_trees(include_events=False)
        assert len(trees) > 0
        tree = trees[0]
        all_nodes = tree.all_nodes()

        event_nodes = [n for n in all_nodes if "SampleEvent" in n.tag]
        assert len(event_nodes) == 0

        span_nodes = [n for n in all_nodes if "SampleEvent" not in n.tag]
        assert len(span_nodes) == 2
    except ImportError:
        pytest.skip("treelib not installed")
