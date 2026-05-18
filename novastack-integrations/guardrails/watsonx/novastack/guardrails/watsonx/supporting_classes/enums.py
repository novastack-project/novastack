from typing import Any

from novastack.common.enums import BaseStrEnum

_REGION_DATA: dict = {
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
    def openscale(self):
        return _REGION_DATA[self.value]["openscale"]

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
