class Action:
    """
    Describes supported action types.

    Attributes:
        BLOCKED (str): "blocked".
        MODIFIED (str): "modified".
        ALLOWED (str): "allowed".
    """

    BLOCKED = "blocked"
    MODIFIED = "modified"
    ALLOWED = "allowed"


class Direction:
    """
    Describes possible directions (input/output).

    Attributes:
        INPUT (str): "input".
        OUTPUT (str): "output".
    """

    INPUT = "input"
    OUTPUT = "output"
