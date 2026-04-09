from typing import Any

from pydantic import Field
from novastack.workflows.types import DictLikeModel


class Event(DictLikeModel):
    """Base class for all workflow events with dict-like interface."""


class StartEvent(Event):
    """Workflow initialization event.

    This event marks the beginning of a workflow execution and can carry
    any dynamic fields needed to initialize the workflow state.
    """


class StopEvent(Event):
    """Workflow completion event.

    This event marks the end of a workflow execution and typically contains
    the final result. Additional dynamic fields can be included as needed.

    Attributes:
        result: The final result of the workflow execution.
    """

    result: Any = Field(
        default=None,
        description="The final result of the workflow execution",
    )
