from enum import Enum

_REGION_DATA = {
    "us-south": {
        "watsonxai": "https://us-south.ml.cloud.ibm.com",
    },
    "eu-de": {
        "watsonxai": "https://eu-de.ml.cloud.ibm.com",
    },
    "au-syd": {
        "watsonxai": "https://au-syd.ml.cloud.ibm.com",
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

    @classmethod
    def from_value(cls, value: str) -> "Region":
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
