from typing import Any

REGION_CONFIG: dict = {
    "au-syd": {
        "watsonx": "https://au-syd.ml.cloud.ibm.com",
    },
    "aws-ap-south": {
        "watsonx": "https://ap-south-1.aws.wxai.ibm.com",
    },
    "eu-de": {
        "watsonx": "https://eu-de.ml.cloud.ibm.com",
    },
    "us-south": {
        "watsonx": "https://us-south.ml.cloud.ibm.com",
    },
}


class RegionValue(str):
    @property
    def watsonx(self) -> str:
        return REGION_CONFIG[self]["watsonx"]

    @property
    def openscale(self) -> str:
        return REGION_CONFIG[self]["openscale"]

    @property
    def factsheet(self) -> str:
        return REGION_CONFIG[self]["factsheet"]


class Region:
    """
    Supported IBM watsonx.governance regions.

    Defines the available regions where watsonx.governance SaaS
    services are deployed.

    Attributes:
        AU_SYD (str): "au-syd".
        AWS_AP_SOUTH (str): "aws-ap-south".
        EU_DE (str): "eu-de".
        US_SOUTH (str): "us-south".
    """

    AU_SYD = RegionValue("au-syd")
    AWS_AP_SOUTH = RegionValue("aws-ap-south")
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
