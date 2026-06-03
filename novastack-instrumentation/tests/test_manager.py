import novastack_instrumentation as instrument
from novastack_instrumentation.dispatcher import root_manager


def test_root_manager_add_dispatcher():
    dispatcher = instrument.get_dispatcher("test")

    assert "root" in root_manager.dispatchers
    assert "test" in root_manager.dispatchers
