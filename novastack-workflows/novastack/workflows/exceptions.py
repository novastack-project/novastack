class WorkflowError(Exception):
    """Generic exception for workflow-related errors."""


class WorkflowValidationError(WorkflowError):
    """Raised when the workflow configuration or step signatures are invalid."""


class WorkflowRuntimeError(WorkflowError):
    """Raised when runtime errors during step execution or event routing."""


class WorkflowTimeoutError(WorkflowError):
    """Raised when a step run exceeds the configured timeout."""


class ContextStateError(WorkflowError):
    """Raised when a context method is called in the wrong state."""
