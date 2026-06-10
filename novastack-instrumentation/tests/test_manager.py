import novastack_instrumentation as instrumentation
from novastack_instrumentation.dispatcher import root_manager


def test_root_manager_add_dispatcher():
    dispatcher = instrumentation.get_dispatcher("test")

    assert "root" in root_manager.dispatchers
    assert "test" in root_manager.dispatchers
