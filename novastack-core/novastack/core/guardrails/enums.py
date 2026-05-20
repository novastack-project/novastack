
class Action:
    """
    Describes supported action types.

    Contains: [BLOCKED, MODIFIED, ALLOWED]
    """

    BLOCKED = "blocked"
    MODIFIED = "modified"
    ALLOWED = "allowed"


class Direction:
    """
    Describes possible directions (input/output).

    Contains: [INPUT, OUTPUT]
    """

    INPUT = "input"
    OUTPUT = "output"
