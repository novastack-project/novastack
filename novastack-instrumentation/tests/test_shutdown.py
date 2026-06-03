from unittest.mock import MagicMock

from novastack_instrumentation._dispatcher_core import Dispatcher, _DispatcherManager
from novastack_instrumentation.observability import BaseObservability


def test_shutdown_calls_close_on_handlers():
    shutdown_mock = MagicMock()

    class TrackingObservability(BaseObservability):
        def shutdown(self) -> None:
            shutdown_mock()

    handler = TrackingObservability()
    d = Dispatcher(handlers=[handler], propagate=False)

    d.shutdown()

    shutdown_mock.assert_called_once()


def test_shutdown_walks_parent_chain():
    parent_shutdown_mock = MagicMock()
    child_shutdown_mock = MagicMock()

    class ParentObservability(BaseObservability):
        def shutdown(self) -> None:
            parent_shutdown_mock()

    class ChildObservability(BaseObservability):
        def shutdown(self) -> None:
            child_shutdown_mock()

    parent_handler = ParentObservability()
    child_handler = ChildObservability()

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

    child.shutdown()

    parent_shutdown_mock.assert_called_once()
    child_shutdown_mock.assert_called_once()


def test_shutdown_is_idempotent():
    shutdown_mock = MagicMock()

    class TrackingObservability(BaseObservability):
        def shutdown(self) -> None:
            shutdown_mock()

    handler = TrackingObservability()
    d = Dispatcher(handlers=[handler], propagate=False)

    d.shutdown()
    d.shutdown()

    assert shutdown_mock.call_count == 2
