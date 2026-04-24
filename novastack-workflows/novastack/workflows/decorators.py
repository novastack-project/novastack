import inspect
from functools import wraps
from typing import Any, Callable, Type, get_origin

from novastack.workflows.events import Event
from novastack.workflows.exceptions import WorkflowValidationError


def step(
    *,
    depends_on: Type[Event] | list[Type[Event]],
    timeout: float | None = None,
    max_retries: int = 0,
    retry_delay: float = 1.0,
) -> Callable:
    """
    Decorator to mark a method as a workflow step.

    The decorated method will be automatically registered as a step
    for the specified event type(s) when the workflow class is defined.

    Args:
        depends_on: The Event class or list of Event classes this step handles.
            - Single event: Step executes when that event arrives
            - List of events: Step executes when all events are collected (join)
        timeout: Optional timeout in seconds for step execution
        max_retries: Number of retry attempts on failure (default: 0)
        retry_delay: Delay in seconds between retry attempts (default: 1)

    Note:
        For event steps, the signature must be:
            async def fn(self, ctx: Context, ev: EventType) -> Event | None

        For join steps, the signature must be:
            async def fn(self, ctx: Context, events: dict[type, Event]) -> Event | None
    """

    def decorator(f: Callable) -> Callable:
        if not inspect.iscoroutinefunction(f):
            raise WorkflowValidationError(
                f"Step method '{f.__name__}' must be an async function."
            )

        # Normalize input: convert single event to list for consistency
        is_join_step = isinstance(depends_on, list)
        events_list: list[Type[Event]] = depends_on if is_join_step else [depends_on]  # type: ignore

        if len(events_list) == 0:
            raise WorkflowValidationError(
                f"Step '{f.__name__}': 'depends_on' cannot be empty. "
                f"Must specify at least one event type."
            )

        seen_event_types = set()
        for event_type in events_list:
            if not (isinstance(event_type, type) and issubclass(event_type, Event)):
                raise WorkflowValidationError(
                    f"Step '{f.__name__}': All event types must be Event subclasses. "
                    f"Got: {event_type}"
                )
            if event_type in seen_event_types:
                raise WorkflowValidationError(
                    f"Step '{f.__name__}': Duplicate event types not allowed. "
                    f"Duplicate: {event_type.__name__}"
                )
            seen_event_types.add(event_type)

        # Validate step signature
        sig = inspect.signature(f)
        params = list(sig.parameters.items())

        if len(params) < 3:
            raise WorkflowValidationError(
                f"Step '{f.__name__}': Must have at least 3 parameters: "
                f"self, ctx, ev/events. Got: {[p[0] for p in params]}"
            )

        # Get the third parameter (event parameter)
        event_param_name, event_param = params[2]

        # Validate signature based on event step vs join step
        if is_join_step:
            # Join step: third param should be 'events' with dict type
            if event_param_name != "events":
                raise WorkflowValidationError(
                    f"Step '{f.__name__}': Join steps must use parameter name "
                    f"'events' (not '{event_param_name}'). "
                    f"Expected signature: async def {f.__name__}(self, ctx: Context, "
                    f"events: dict[type, Event]) -> Event | None"
                )

            # Check type annotation if present
            if event_param.annotation != inspect.Parameter.empty:
                annotation = event_param.annotation
                # Handle dict[type, Event] or dict type annotations
                origin = get_origin(annotation)
                if origin is not dict and annotation is not dict:
                    raise WorkflowValidationError(
                        f"Step '{f.__name__}': Join steps must annotate 'events' "
                        f"parameter as 'dict[type, Event]' or 'dict'. "
                        f"Got: {annotation}"
                    )
        else:
            # Event step: third param should be 'ev'
            if event_param_name != "ev":
                raise WorkflowValidationError(
                    f"Step '{f.__name__}': Event steps must use parameter name "
                    f"'ev' (not '{event_param_name}'). "
                    f"Expected signature: async def {f.__name__}(self, ctx: Context, "
                    f"ev: {events_list[0].__name__}) -> Event | None"
                )

        # Store metadata on the function
        f._step_metadata_ = {
            "depends_on": events_list,
            "is_join_step": is_join_step,
            "timeout": timeout,
            "max_retries": max_retries,
            "retry_delay": retry_delay,
        }

        @wraps(f)
        async def wrapper(*args, **kwargs):
            return await f(*args, **kwargs)

        # Copy metadata to wrapper
        wrapper._step_metadata_ = f._step_metadata_

        return wrapper  # type: ignore

    return decorator


def is_step_method(method: Any) -> bool:
    """Check if a method is decorated with @step."""
    return hasattr(method, "_step_metadata_")


def get_step_event_types(method: Any) -> list[Type[Event]] | None:
    """Get the normalized list of event types that a step method handles."""
    metadata = getattr(method, "_step_metadata_", None)
    if metadata is None:
        return None
    return metadata.get("depends_on")


def is_join_step(method: Any) -> bool:
    metadata = getattr(method, "_step_metadata_", None)
    if metadata is None:
        return False
    return metadata.get("is_join_step", False)


def get_step_name(method: Any) -> str | None:
    """Get the name of a step method."""
    if not is_step_method(method):
        return None
    return method.__name__ if hasattr(method, "__name__") else None


def get_step_timeout(method: Any) -> float | None:
    """Get the timeout configuration for a step method."""
    metadata = getattr(method, "_step_metadata_", None)
    if metadata is None:
        return None
    return metadata.get("timeout")


def get_step_max_retries(method: Any) -> int:
    """Get the max retries configuration for a step method."""
    metadata = getattr(method, "_step_metadata_", None)
    if metadata is None:
        return 0
    return metadata.get("max_retries", 0)


def get_step_retry_delay(method: Any) -> float:
    """Get the retry delay configuration for a step method."""
    metadata = getattr(method, "_step_metadata_", None)
    if metadata is None:
        return 1.0
    return metadata.get("retry_delay", 1.0)
