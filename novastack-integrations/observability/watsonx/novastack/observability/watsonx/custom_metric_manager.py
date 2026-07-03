import warnings

from novastack.observability.watsonx.client import WatsonxGovClient


class WatsonxCustomMetricsManager(WatsonxGovClient):
    """
    Deprecated: Use `WatsonxGovClient` instead.
    """

    def __init__(self, **data):
        warnings.warn(
            "WatsonxCustomMetricsManager is deprecated and will be removed in a future version. "
            "Use WatsonxGovClient instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**data)


__all__ = ["WatsonxCustomMetricsManager"]
