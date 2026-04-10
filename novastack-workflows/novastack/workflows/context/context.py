import asyncio
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from novastack.workflows.context.state_store import StateStore
from novastack.workflows.runtime.optimized_queue import OptimizedEventQueue
from pydantic import BaseModel

if TYPE_CHECKING:
    from novastack.workflows.events import Event

STATE_T = TypeVar("STATE_T", bound=BaseModel)


class Context(Generic[STATE_T]):
    """
    Workflow execution context with copy-on-write state management.

    Provides robust, immutable state management through 'state_store'.

    State is automatically initialized based on the type annotation.
    If no type is provided, uses DictLikeModel.

    Example:
        ```python
        class RunState(BaseModel):
            counter: int = 0
            items: list[str] = []


        # With typed state - auto-initialized
        @step
        async def start(self, ctx: Context[RunState], ev: StartEvent):
            async with ctx.store.edit_state() as state:
                state.counter += 1  # RunState auto-initialized


        # Without type - uses DictLikeModel
        @step
        async def start(self, ctx: Context, ev: StartEvent):
            async with ctx.store.edit_state() as state:
                state.counter = 1  # DictLikeModel allows dynamic fields
        ```
    """

    def __init__(
        self,
        workflow: Any,
        event_queue: asyncio.Queue["Event"] | Any | None = None,
    ):
        """
        Initialize workflow context.

        Each context is isolated and maintains its own state store.
        State type is inferred from Context[StateType] annotation or defaults to DictLikeModel.

        Args:
            workflow: Workflow instance
            event_queue: Event queue for emission
        """
        self._workflow = workflow

        # Use provided queue or create OptimizedEventQueue
        if event_queue is None:
            self._event_queue = OptimizedEventQueue()
        else:
            self._event_queue = event_queue

        # Copy-on-write state store with auto-initialization
        # Infer state type from workflow's _state_type if available
        state_type = getattr(workflow, "_state_type", None)
        self._store = StateStore(state_type=state_type)

    @property
    def workflow(self) -> Any:
        """Get workflow instance."""
        return self._workflow

    @property
    def store(self) -> StateStore:
        """
        Copy-on-write state store.

        Provides immutability guarantees and thread-safety through
        explicit edit contexts.

        Example:
            ```python
            # Edit state
            async with ctx.store.edit_state() as state:
                state.counter += 1
            ```
        """
        return self._store

    @property
    def state(self) -> BaseModel | None:
        """
        Get current state (read-only).

        Convenience property for accessing store state.
        Equivalent to ctx.store.state.

        Example:
            ```python
            # Read-only access
            current_value = ctx.state.counter
            ```
        """
        return self._store.state

    async def emit(self, event: "Event") -> None:
        """
        Emit an event to the workflow queue.

        Args:
            event: Event to emit

        Example:
            ```python
            await ctx.emit(MyEvent(data="processed"))
            ```
        """
        await self._event_queue.put(event)
