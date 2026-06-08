import novastack_telemetry as telemetry
from novastack_telemetry.observability.novastack_debug import (
    NovastackDebugObservability,
)


def test_set_global_handler_on_new_dispatcher():
    """Test that new dispatchers automatically get global handlers."""
    handler = NovastackDebugObservability(print_span_on_end=False)
    telemetry.set_global_handler(handler)

    dispatcher = telemetry.get_dispatcher("test_global_handler")

    assert handler in dispatcher.handlers
    assert len(dispatcher.handlers) >= 1
