from novastack_instrumentation._dispatcher_core import Dispatcher, _DispatcherManager

root_dispatcher: Dispatcher = Dispatcher(
    name="root",
    handlers=[],
    propagate=False,
)

root_manager: _DispatcherManager = _DispatcherManager(root_dispatcher)


def get_dispatcher(name: str = "root") -> Dispatcher:
    """
    Get or create a Dispatcher by name with hierarchical parent resolution.

    Returns existing dispatcher or creates a new one. Parent is determined by
    dot-notation hierarchy (e.g., "a.b.c" → parent "a.b"), falling back to "root".

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

    # Create and register new dispatcher
    new_dispatcher = Dispatcher(
        name=name,
        root_name=root_dispatcher.name,
        parent_name=parent_name,
        dispatcher_manager=root_manager,
    )
    root_manager.add_dispatcher(new_dispatcher)

    return new_dispatcher
