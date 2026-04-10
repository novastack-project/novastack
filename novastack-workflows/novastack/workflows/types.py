from typing import Any

from novastack.workflows.enums import WorkflowStatus
from pydantic import BaseModel, ConfigDict, Field


class DictLikeModel(BaseModel):
    """
    A Pydantic model that works like a dictionary for dynamic fields.

    This class provides a Pydantic-based class system that supports both
    attribute access (event.field) and dictionary-style access (event["field"]).
    """

    model_config = ConfigDict(
        extra="allow",
        arbitrary_types_allowed=True,
    )

    def __getitem__(self, key: str) -> Any:
        """Support event["field"] access."""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Support event["field"] = value assignment."""
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        """Support 'field' in event membership test."""
        return hasattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a field value with a default fallback."""
        return getattr(self, key, default)

    def keys(self) -> list[str]:
        """Return list of field names."""
        return list(self.model_dump().keys())

    def values(self) -> list[Any]:
        """Return list of field values."""
        return list(self.model_dump().values())

    def items(self) -> list[tuple[str, Any]]:
        """Return list of (field_name, value) tuples."""
        return list(self.model_dump().items())


class WorkflowResult(BaseModel):
    """
    Workflow execution result.

    This class encapsulates all information about a completed workflow run,
    including its final result, execution metrics, and status.

    Attributes:
        run_id: Unique identifier for this workflow run/execution.
        iterations: Number of iterations executed during the workflow run.
        status: Execution status indicating completion, failure, or cancellation.
        result: Final result from StopEvent, None if workflow didn't complete normally.
        error: Error message if the workflow failed, None otherwise.
    """

    model_config = ConfigDict(validate_assignment=True)

    run_id: str = Field(
        ...,
        description="Unique identifier for this workflow run/execution",
    )
    num_iterations: int = Field(
        ...,
        description="Number of iterations executed",
        ge=0,
    )
    status: WorkflowStatus = Field(
        ...,
        description="Execution status",
    )
    result: Any | None = Field(
        default=None,
        description="Final result from StopEvent",
    )
    warnings: str | None = Field(
        default=None,
        description="Warning message",
    )
