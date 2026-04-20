from enum import Enum


class Action(str, Enum):
    BLOCKED = "blocked"
    MODIFIED = "modified"
    ALLOWED = "allowed"


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
    def enum_validate(cls, value: str) -> "Direction":
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
