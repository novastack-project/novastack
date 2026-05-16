from typing import Any

from novastack.core.base.enum import BaseStrEnum

_REGION_DATA: dict = {
    "us-south": {
        "watsonx": "https://us-south.ml.cloud.ibm.com",
        "openscale": "https://api.aiopenscale.cloud.ibm.com",
        "factsheet": "dallas",
    },
    "eu-de": {
        "watsonx": "https://eu-de.ml.cloud.ibm.com",
        "openscale": "https://eu-de.api.aiopenscale.cloud.ibm.com",
        "factsheet": "frankfurt",
    },
    "au-syd": {
        "watsonx": "https://au-syd.ml.cloud.ibm.com",
        "openscale": "https://au-syd.api.aiopenscale.cloud.ibm.com",
        "factsheet": "sydney",
    },
}


class Region(BaseStrEnum):
    """
    Supported IBM watsonx.governance regions.

    Defines the available regions where watsonx.governance SaaS
    services are deployed.

    Attributes:
        US_SOUTH (str): "us-south".
        EU_DE (str): "eu-de".
        AU_SYD (str): "au-syd".
    """

    US_SOUTH = "us-south"
    EU_DE = "eu-de"
    AU_SYD = "au-syd"

    @property
    def watsonx(self):
        return _REGION_DATA[self.value]["watsonx"]

    @property
    def openscale(self):
        return _REGION_DATA[self.value]["openscale"]

    @property
    def factsheet(self):
        return _REGION_DATA[self.value]["factsheet"]

    @classmethod
    def from_value(cls, value: Any) -> "Region":
        if value is None:
            return cls(Region.US_SOUTH)

        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            try:
                return cls(value.lower())
            except ValueError:
                raise ValueError(
                    "Invalid value for Region. "
                    "Received: '{}'. Valid values are: {}.".format(
                        value, [item.value for item in Region]
                    )
                )

        raise TypeError(
            f"Invalid type for Region. "
            f"Expected str or Region, but received {type(value).__name__}."
        )


class TaskType(BaseStrEnum):
    """
    Supported IBM watsonx.governance tasks.

    Attributes:
        QUESTION_ANSWERING (str): "question_answering"
        SUMMARIZATION (str): "summarization"
        RETRIEVAL_AUGMENTED_GENERATION (str): "retrieval_augmented_generation"
        CLASSIFICATION (str): "classification"
        GENERATION (str): "generation"
        CODE (str): "code"
        EXTRACTION (str): "extraction"
    """

    QUESTION_ANSWERING = "question_answering"
    SUMMARIZATION = "summarization"
    RETRIEVAL_AUGMENTED_GENERATION = "retrieval_augmented_generation"
    CLASSIFICATION = "classification"
    GENERATION = "generation"
    CODE = "code"
    EXTRACTION = "extraction"


class DataSetType(BaseStrEnum):
    """
    Supported IBM watsonx.governance tasks.

    Attributes:
        PAYLOAD (str): "payload"
        FEEDBACK (str): "feedback"
    """

    PAYLOAD = "payload"
    FEEDBACK = "feedback"
