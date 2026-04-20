from enum import Enum

_REGION_DATA = {
    "us-south": {
        "watsonxai": "https://us-south.ml.cloud.ibm.com",
        "openscale": "https://api.aiopenscale.cloud.ibm.com",
        "factsheet": "dallas",
    },
    "eu-de": {
        "watsonxai": "https://eu-de.ml.cloud.ibm.com",
        "openscale": "https://eu-de.api.aiopenscale.cloud.ibm.com",
        "factsheet": "frankfurt",
    },
    "au-syd": {
        "watsonxai": "https://au-syd.ml.cloud.ibm.com",
        "openscale": "https://au-syd.api.aiopenscale.cloud.ibm.com",
        "factsheet": "sydney",
    },
}


class Region(str, Enum):
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
    def watsonxai(self):
        return _REGION_DATA[self.value]["watsonxai"]

    @property
    def openscale(self):
        return _REGION_DATA[self.value]["openscale"]

    @property
    def factsheet(self):
        return _REGION_DATA[self.value]["factsheet"]

    @classmethod
    def enum_validate(cls, value: str) -> "Region":
        if value is None:
            return cls.US_SOUTH

        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            try:
                return cls(value.lower())
            except ValueError:
                raise ValueError(
                    "Invalid value for parameter 'region'. Received: '{}'. Valid values are: {}.".format(
                        value, [item.value for item in Region]
                    )
                )

        raise TypeError(
            f"Invalid type for parameter 'region'. Expected str or Region, but received {type(value).__name__}."
        )


class TaskType(str, Enum):
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

    @classmethod
    def enum_validate(cls, value: str) -> "TaskType":
        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            try:
                return cls(value.lower())
            except ValueError:
                raise ValueError(
                    "Invalid value for parameter 'task_id'. Received: '{}'. Valid values are: {}.".format(
                        value, [item.value for item in TaskType]
                    )
                )

        raise TypeError(
            f"Invalid type for parameter 'task_id'. Expected str or TaskType, but received {type(value).__name__}."
        )


class DataSetType(str, Enum):
    """
    Supported IBM watsonx.governance tasks.

    Attributes:
        PAYLOAD (str): "payload"
        FEEDBACK (str): "feedback"
    """

    PAYLOAD = "payload"
    FEEDBACK = "feedback"

    @classmethod
    def enum_validate(cls, value: str) -> "DataSetType":
        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            try:
                return cls(value.lower())
            except ValueError:
                raise ValueError(
                    "Invalid value. Received: '{}'. Valid values are: {}.".format(
                        value, [item.value for item in DataSetType]
                    )
                )

        raise TypeError(
            f"Invalid type. Expected str or DataSetType, but received {type(value).__name__}."
        )
