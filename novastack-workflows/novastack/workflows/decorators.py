import inspect
from functools import wraps
from typing import Any, Callable, Type

from novastack.workflows.events import Event
from novastack.workflows.exceptions import WorkflowValidationError


def step(
    *,
    on: Type[Event],
    timeout: float | None = None,
    max_retries: int = 0,
    retry_delay: float = 1.0,
) -> Callable:
    """
    Decorator to mark a method as a workflow step.

    The decorated method will be automatically registered as a step
    for the specified event type when the workflow class is defined.

    Args:
        on: The Event class this step handles.
        timeout: Optional timeout in seconds for step execution
        max_retries: Number of retry attempts on failure (default: 0)
        retry_delay: Delay in seconds between retry attempts (default: 1)

    Note:
        The decorated method must have the signature:
        async def fn(self, ctx: Context, ev: EventType) -> Event | None
    """

    def decorator(f: Callable) -> Callable:
        # Is async function?
        if not inspect.iscoroutinefunction(f):
            raise WorkflowValidationError(
                f"Step method '{f.__name__}' must be an async function."
            )

        # Validate step signature
        sig = inspect.signature(f)
        params = list(sig.parameters.keys())

        if len(params) < 3:
            raise WorkflowValidationError(
                f"Step signature '{f.__name__}' must have at least 3 parameters: "
                f"self, ctx, ev. got: {params}"
            )

        # Store metadata on the function
        f.__workflow_step__ = True
        f.__step_accepted_events__ = on
        f.__step_name__ = f.__name__
        f.__step_timeout__ = timeout
        f.__step_max_retries__ = max_retries
        f.__step_retry_delay__ = retry_delay

        @wraps(f)
        async def wrapper(*args, **kwargs):
            return await f(*args, **kwargs)

        # Copy metadata to wrapper
        wrapper.__workflow_step__ = True
        wrapper.__step_accepted_events__ = on
        wrapper.__step_name__ = f.__name__
        wrapper.__step_timeout__ = timeout
        wrapper.__step_max_retries__ = max_retries
        wrapper.__step_retry_delay__ = retry_delay

        return wrapper  # type: ignore

    return decorator


def is_step_method(method: Any) -> bool:
    """
    Check if a method is decorated with @step.
    """
    return getattr(method, "__workflow_step__", False)


def get_step_event_type(method: Any) -> Type[Event] | None:
    """
    Get the event type that a step method handles.
    """
    return getattr(method, "__step_accepted_events__", None)


def get_step_name(method: Any) -> str | None:
    """
    Get the name of a step method.
    """
    return getattr(method, "__step_name__", None)


def get_step_timeout(method: Any) -> float | None:
    """
    Get timeout for a step method.
    """
    return getattr(method, "__step_timeout__", None)


def get_step_max_retries(method: Any) -> int:
    """
    Get number of retries for a step method.
    """
    return getattr(method, "__step_max_retries__", 0)


def get_step_retry_delay(method: Any) -> float:
    """
    Get retry delay for a step method.
    """
    return getattr(method, "__step_retry_delay__", 1.0)
