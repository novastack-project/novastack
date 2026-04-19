from enum import Enum


class Action(str, Enum):
    BLOCKED = "blocked"
    MODIFIED = "modified"
    ALLOWED = "allowed"
