import novastack_instrumentation as instrumentation
from novastack_instrumentation.observability import (
    DebugObservability,
)


def test_set_global_handler_on_new_dispatcher():
    """Test that new dispatchers automatically get global handlers."""
    handler = DebugObservability(print_span_on_end=False)
    instrumentation.set_global_handler(handler)

    dispatcher = instrumentation.get_dispatcher("test_global_handler")

    assert handler in dispatcher.handlers
    assert len(dispatcher.handlers) >= 1
