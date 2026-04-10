from enum import Enum

_REGION_DATA = {
    "us-south": {
        "openscale": "https://api.aiopenscale.cloud.ibm.com",
    },
    "eu-de": {
        "openscale": "https://eu-de.api.aiopenscale.cloud.ibm.com",
    },
    "au-syd": {
        "openscale": "https://au-syd.api.aiopenscale.cloud.ibm.com",
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
    def openscale(self):
        return _REGION_DATA[self.value]["openscale"]

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


class Direction(str, Enum):
    """
    Supported IBM watsonx.governance directions (input/output).

    Attributes:
        INPUT (str): "input".
        OUTPUT (str): "output".
    """

    INPUT = "input"
    OUTPUT = "output"

    @classmethod
    def from_value(cls, value: str) -> "Direction":
        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            try:
                return cls(value.lower())
            except ValueError:
                raise ValueError(
                    "Invalid value for parameter 'direction'. Received: '{}'. Valid values are: {}.".format(
                        value, [item.value for item in Direction]
                    )
                )

        raise TypeError(
            f"Invalid type for parameter 'direction'. Expected str or Direction, but received {type(value).__name__}."
        )
