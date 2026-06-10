from novastack_instrumentation._core import Dispatcher, DispatcherManager
from novastack_instrumentation.observability import BaseObservability

_global_handlers: list[BaseObservability] = []

root_dispatcher: Dispatcher = Dispatcher(
    name="root",
    handlers=[],
    propagate=False,
)

root_manager: DispatcherManager = DispatcherManager(root_dispatcher)


def set_global_handler(handler: BaseObservability) -> None:
    """
    Add a handler to the global handlers list.

    Global handlers are automatically added to all dispatchers (including root)
    and any new dispatchers created after this call.

    Args:
        handler: The observability handler to add globally.

    Example:
        ```python
        from novastack_instrumentation import set_global_handler, get_dispatcher
        from novastack_instrumentation.observability import ConsoleObservability

        # Set global handler once
        handler = ConsoleObservability()
        set_global_handler(handler)
        ```
    """
    if handler not in _global_handlers:
        _global_handlers.append(handler)

        if handler not in root_dispatcher.handlers:
            root_dispatcher.add_handler(handler)

        for dispatcher in root_manager.dispatchers.values():
            if handler not in dispatcher.handlers:
                dispatcher.add_handler(handler)


def get_global_handlers() -> list[BaseObservability]:
    """
    Get the list of global observability handlers.

    Returns:
        List of global observability handlers.
    """
    return _global_handlers.copy()


def get_dispatcher(name: str = "root") -> Dispatcher:
    """
    Get or create a Dispatcher by name with hierarchical parent resolution.

    Returns existing dispatcher or creates a new one. Parent is determined by
    dot-notation hierarchy (e.g., "a.b.c" → parent "a.b"), falling back to "root".

    Global handlers (set via set_global_handler) are automatically added to
    all new dispatchers.

    Args:
        name: The name of the dispatcher. Defaults to "root".
    """
    # Return existing dispatcher if found
    if existing := root_manager.dispatchers.get(name):
        return existing

    # Determine parent: try hierarchical parent first, fallback to root
    candidate_parent_name = ".".join(name.split(".")[:-1])
    parent_name = (
        candidate_parent_name
        if candidate_parent_name in root_manager.dispatchers
        else "root"
    )

    # Create and register new dispatcher with global handlers
    new_dispatcher = Dispatcher(
        name=name,
        root_name=root_dispatcher.name,
        parent_name=parent_name,
        dispatcher_manager=root_manager,
        handlers=_global_handlers.copy(),
    )
    root_manager.add_dispatcher(new_dispatcher)

    return new_dispatcher
