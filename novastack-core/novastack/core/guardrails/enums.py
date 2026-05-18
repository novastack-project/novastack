from novastack.common.enums import BaseStrEnum


class Action(BaseStrEnum):
    BLOCKED = "blocked"
    MODIFIED = "modified"
    ALLOWED = "allowed"


class Direction(BaseStrEnum):
    """
    Supported IBM watsonx.governance directions (input/output).

    Attributes:
        INPUT (str): "input".
        OUTPUT (str): "output".
    """

    INPUT = "input"
    OUTPUT = "output"
