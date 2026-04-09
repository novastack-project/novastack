from enum import Enum


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    RUNNING = "running"
