from typing import Literal

from novastack.core.bridge.pydantic import BaseModel


class WatsonxMetricThreshold(BaseModel):
    """
    Defines the metric threshold for IBM watsonx.governance.

    Attributes:
        threshold_type (str): The threshold type. Can be either `lower_limit` or `upper_limit`.
        default_value (float): The metric threshold value.

    Example:
        ```python
        from novastack.observability.watsonx import WatsonxMetricThreshold

        WatsonxMetricThreshold(threshold_type="lower_limit", default_value=0.8)
        ```
    """

    threshold_type: Literal["lower_limit", "upper_limit"]
    default_value: float | None = None

    def to_dict(self) -> dict:
        return {"type": self.threshold_type, "default": self.default_value}


class WatsonxMetricSpec(BaseModel):
    """
    Defines the IBM watsonx.governance global monitor metric.

    Attributes:
        name (str): The name of the metric.
        applies_to (list[str]): A list of task types that the metric applies to. Currently supports:
            "summarization", "generation", "question_answering", "extraction", and "retrieval_augmented_generation".
        thresholds (list[WatsonxMetricThreshold]): A list of metric thresholds associated with the metric.

    Example:
        ```python
        from novastack.observability.watsonx import (
            WatsonxMetricSpec,
            WatsonxMetricThreshold,
        )

        WatsonxMetricSpec(
            name="context_quality",
            applies_to=["retrieval_augmented_generation", "summarization"],
            thresholds=[
                WatsonxMetricThreshold(threshold_type="lower_limit", default_value=0.75)
            ],
        )
        ```
    """

    name: str
    applies_to: list[
        Literal[
            "summarization",
            "generation",
            "question_answering",
            "extraction",
            "retrieval_augmented_generation",
        ]
    ]
    thresholds: list[WatsonxMetricThreshold] | None = None

    def to_dict(self) -> dict:
        from ibm_watson_openscale.base_classes.watson_open_scale_v2 import (
            ApplicabilitySelection,
            MetricThreshold,
        )

        monitor_metric = {
            "name": self.name,
            "applies_to": ApplicabilitySelection(problem_type=self.applies_to),
        }

        if self.thresholds is not None:
            monitor_metric["thresholds"] = [
                MetricThreshold(**threshold.to_dict()) for threshold in self.thresholds
            ]

        return monitor_metric
