import novastack_telemetry as telemetry
from novastack_telemetry.dispatcher import root_manager


def test_root_manager_add_dispatcher():
    dispatcher = telemetry.get_dispatcher("test")

    assert "root" in root_manager.dispatchers
    assert "test" in root_manager.dispatchers
