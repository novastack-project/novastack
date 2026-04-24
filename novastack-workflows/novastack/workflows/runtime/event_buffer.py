import asyncio
from typing import Any

from novastack.workflows.events import Event


class EventBuffer:
    """
    Thread-safe event buffer for multi-event step coordination.

    Stores events until all required events for a step are collected,
    enabling fan-in patterns where a step waits for multiple
    different event types before executing.

    The buffer uses a two-level dictionary structure:
    - First level: keyed by step name
    - Second level: keyed by event type

    Thread Safety:
        All public methods use asyncio.Lock to ensure thread-safe access
        to the internal buffer structure.
    """

    def __init__(self):
        self._buffer: dict[str, dict[type, Event]] = {}
        self._lock = asyncio.Lock()

    async def add_event(self, step_name: str, event: Event) -> None:
        """
        Add event to buffer for a specific step.

        If an event of the same type already exists for this step,
        it will be overwritten with the new event (latest wins strategy).
        This ensures that duplicate events don't accumulate in the buffer.

        Args:
            step_name: Name of the step waiting for events.
            event: Event instance to store. The event's type is used as
                the key within the step's event collection.

        Thread Safety:
            This method is thread-safe and can be called concurrently
            from multiple tasks.
        """
        async with self._lock:
            if step_name not in self._buffer:
                self._buffer[step_name] = {}

            # Store event keyed by its type (overwrites if duplicate)
            event_type = type(event)
            self._buffer[step_name][event_type] = event

    async def get_events(
        self, step_name: str, required_events: set[type]
    ) -> dict[type, Event] | None:
        """
        Get all events for a step if complete.

        Retrieves all events for a step if all required event types are
        present. This method does NOT clear the events from the buffer;
        use clear_events() separately after successful step execution.

        Args:
            step_name: Name of the step to retrieve events for.
            required_events: Set of event types that must all be present.
                Only returns events if ALL required types are available.

        Returns:
            Dictionary mapping event types to event instances if all
            required events are present, None otherwise. The returned
            dictionary contains only the required event types.

        Thread Safety:
            This method is thread-safe and can be called concurrently
            from multiple tasks.

        Example:
            >>> await buffer.add_event("join_step", EventA(data="a"))
            >>> await buffer.add_event("join_step", EventB(data="b"))
            >>> events = await buffer.get_events("join_step", {EventA, EventB})
            >>> if events:
            ...     event_a = events[EventA]
            ...     event_b = events[EventB]
        """
        async with self._lock:
            if step_name not in self._buffer:
                return None

            stored_events = self._buffer[step_name]
            stored_types = set(stored_events.keys())

            # Check if all required events are present
            if not required_events.issubset(stored_types):
                return None

            # Return only the required events
            return {
                event_type: stored_events[event_type] for event_type in required_events
            }

    async def clear_events(self, step_name: str) -> None:
        """
        Clear all events for a step from buffer.

        Removes all events associated with the specified step from
        the buffer. This should be called after successful step execution
        to prevent memory leaks and ensure clean state.

        If the step name doesn't exist in the buffer, this method
        does nothing (no error is raised).

        Args:
            step_name: Name of the step to clear. All events for this
                step will be removed from the buffer.

        Thread Safety:
            This method is thread-safe and can be called concurrently
            from multiple tasks.

        Example:
            >>> await buffer.add_event("join_step", EventA())
            >>> await buffer.clear_events("join_step")
            >>> events = await buffer.get_events("join_step", {EventA})
            >>> assert events is None  # Buffer is empty for this step
        """
        async with self._lock:
            if step_name in self._buffer:
                del self._buffer[step_name]

    def get_buffer_size(self) -> int:
        """
        Get total number of events in buffer.

        Returns the total count of events stored across all steps.

        Note: This method is synchronous and does not acquire the lock,
        so the returned value may be slightly stale in highly concurrent
        scenarios. However, it's safe to call and won't cause corruption.

        Returns:
            Total count of stored events. Returns 0 if the buffer is empty.

        Example:
            >>> await buffer.add_event("step1", EventA())
            >>> await buffer.add_event("step1", EventB())
            >>> await buffer.add_event("step2", EventC())
            >>> buffer.get_buffer_size()
            3
        """
        return sum(len(events) for events in self._buffer.values())

    def get_pending_steps(self) -> list[str]:
        """
        Get list of step names with pending events.

        This method returns all step names that currently have events
        stored in the buffer. Useful for debugging and monitoring to
        identify which steps are waiting for additional events.

        Returns:
            List of step names that have events in buffer.
            Returns empty list if buffer is empty.

        Thread Safety:
            This method is synchronous and does not acquire the lock,
            so the returned value may be slightly stale in highly concurrent
            scenarios. However, it's safe to call and won't cause corruption.

        Example:
            >>> await buffer.add_event("step1", EventA())
            >>> await buffer.add_event("step2", EventB())
            >>> buffer.get_pending_steps()
            ['step1', 'step2']
        """
        return list(self._buffer.keys())

    def get_step_status(self, step_name: str) -> dict[str, Any]:
        """
        Get status of a specific step's buffered events.

        Returns information about which event types have been received
        for a specific step. This is useful for debugging to understand
        which events are present and which are still missing.

        Args:
            step_name: Name of the step to check.

        Returns:
            Dictionary mapping event type names to True (indicating presence).
            Returns empty dict if step has no buffered events.

        Thread Safety:
            This method is synchronous and does not acquire the lock,
            so the returned value may be slightly stale in highly concurrent
            scenarios. However, it's safe to call and won't cause corruption.
        """
        if step_name not in self._buffer:
            return {}

        return {
            event_type.__name__: True for event_type in self._buffer[step_name].keys()
        }
