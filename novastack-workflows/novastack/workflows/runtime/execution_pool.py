import asyncio
from typing import Any, Callable, Coroutine


class StepExecutionPool:
    """Pool for executing workflow steps with controlled concurrency."""

    def __init__(self, max_workers: int = 100):
        self._semaphore = asyncio.Semaphore(max_workers)
        self._active_tasks = 0
        self._lock = asyncio.Lock()

    async def execute(
        self, func: Callable[..., Coroutine[Any, Any, Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """
        Execute a step function with concurrency control.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        async with self._semaphore:
            async with self._lock:
                self._active_tasks += 1

            try:
                return await func(*args, **kwargs)
            finally:
                async with self._lock:
                    self._active_tasks -= 1

    async def execute_batch(
        self, tasks: list[tuple[Callable, tuple, dict]]
    ) -> list[Any]:
        """
        Execute a batch of steps concurrently.

        Args:
            tasks: List of (func, args, kwargs) tuples
        """
        coroutines = [
            self.execute(func, *args, **kwargs) for func, args, kwargs in tasks
        ]
        return await asyncio.gather(*coroutines)

    @property
    def active_tasks(self) -> int:
        """Get number of currently active tasks."""
        return self._active_tasks
