from typing import Any

REGION_CONFIG: dict = {
    "au-syd": {
        "openscale": "https://au-syd.api.aiopenscale.cloud.ibm.com",
    },
    "eu-de": {
        "openscale": "https://eu-de.api.aiopenscale.cloud.ibm.com",
    },
    "us-south": {
        "openscale": "https://api.aiopenscale.cloud.ibm.com",
    },
}


class RegionValue(str):

    @property
    def openscale(self) -> str:
        return REGION_CONFIG[self]["openscale"]


class Region:
    """
    Supported IBM watsonx.governance regions.

    Defines the available regions where watsonx.governance SaaS
    services are deployed.

    Attributes:
        AU_SYD (str): "au-syd".
        EU_DE (str): "eu-de".
        US_SOUTH (str): "us-south".
    """

    AU_SYD = RegionValue("au-syd")
    EU_DE = RegionValue("eu-de")
    US_SOUTH = RegionValue("us-south")

    @classmethod
    def from_value(cls, value: Any) -> "RegionValue":
        if value is None:
            return cls.US_SOUTH

        if isinstance(value, RegionValue):
            return value

        if isinstance(value, str):
            value = value.lower()

            for region in (getattr(cls, name) for name in vars(cls) if name.isupper()):
                if region == value:
                    return region

            raise ValueError("Invalid value for Region: '{}'.".format(value))

        raise TypeError(
            f"Invalid type for Region. "
            f"Expected str or Region, but received {type(value).__name__}."
        )
