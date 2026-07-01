import warnings

from novastack.observability.watsonx.aigov_client import WatsonxGovClient


class WatsonxMonitorManager(WatsonxGovClient):
    """
    Deprecated: Use `WatsonxGovClient` with `setup_monitor()` instead.
    """

    def __init__(self, **data):
        warnings.warn(
            "WatsonxMonitorManager is deprecated and will be removed in a future version. "
            "Use WatsonxGovClient instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**data)


__all__ = ["WatsonxMonitorManager"]
