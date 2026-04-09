class WorkflowValidationError(Exception):
    """Raised when the workflow configuration or step signatures are invalid."""


class WorkflowRuntimeError(Exception):
    """Raised when runtime errors during step execution or event routing."""


class WorkflowTimeoutError(Exception):
    """Raised when a step run exceeds the configured timeout."""


class ContextStateError(Exception):
    """Raised when a context method is called in the wrong state."""
