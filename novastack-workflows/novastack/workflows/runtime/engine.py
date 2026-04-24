import asyncio
import uuid
from typing import TYPE_CHECKING, Any

from novastack.workflows.context import Context
from novastack.workflows.decorators import (
    get_step_max_retries,
    get_step_retry_delay,
    get_step_timeout,
)
from novastack.workflows.events import Event, StartEvent, StopEvent
from novastack.workflows.exceptions import (
    WorkflowRuntimeError,
    WorkflowTimeoutError,
    WorkflowValidationError,
)
from novastack.workflows.runtime.event_buffer import EventBuffer
from novastack.workflows.runtime.execution_pool import StepExecutionPool
from novastack.workflows.runtime.optimized_queue import OptimizedEventQueue
from novastack.workflows.types import WorkflowResult, WorkflowStatus

if TYPE_CHECKING:
    from novastack.workflows import Workflow


class WorkflowEngine:
    """
    Executes workflow steps based on event-driven architecture.

    The WorkflowEngine manages the execution of decorator-based workflow steps
    by processing events through an event queue. It handles event dispatching,
    parallel step execution (fan-out), error handling, and iteration limits.

    Attributes:
        workflow: The workflow instance containing decorated step methods.
        max_iterations: Maximum number of event processing iterations allowed. Use 0 for unlimited iterations.
        queue_wait_timeout: Timeout in seconds for queue operations.
        max_workers: Maximum concurrent step executions.
                Defaults to 100.
        max_buffer_size: Maximum number of events that can be buffered (default: 1000).
    """

    def __init__(
        self,
        workflow: "Workflow",
        max_iterations: int = 1000,
        queue_wait_timeout: float = 1.0,
        max_workers: int = 100,
        max_buffer_size: int = 1000,
    ) -> None:
        if max_iterations < 0:
            raise WorkflowValidationError(
                "'max_iterations' must be 0 (unlimited) or greater"
            )
        if queue_wait_timeout <= 0:
            raise WorkflowValidationError("'queue_wait_timeout' must be greater than 0")
        if max_buffer_size <= 0:
            raise WorkflowValidationError("'max_buffer_size' must be greater than 0")

        self._workflow = workflow
        self._max_iterations = max_iterations
        self._queue_wait_timeout = queue_wait_timeout
        self._pool = StepExecutionPool(max_workers)
        self._event_buffer = EventBuffer()
        self._max_buffer_size = max_buffer_size

    async def run(
        self,
        start_events: list[StartEvent] | StartEvent,
        ctx: Context | None = None,
    ) -> WorkflowResult:
        """
        Execute the workflow with initial events.

        This is the main entry point for workflow execution. It creates a
        Context (if not provided), enqueues initial events, and processes
        the event queue until completion or max_iterations is reached.

        Args:
            start_events: Single event or list of events to start the workflow.
            ctx: Optional pre-configured context with optional state data.

        Returns:
            WorkflowResult containing the final result, iteration count, status,
            and any error information.

        Note:
            The workflow continues processing events until the queue is empty,
            a StopEvent is encountered, or max_iterations is reached. Steps are
            executed in parallel when multiple steps listen to the same event
            type (fan-out pattern).
        """
        run_id = str(uuid.uuid4())

        # Initialize optimized event queue
        event_queue: OptimizedEventQueue[Event] = OptimizedEventQueue()

        # Create or use provided context
        if ctx is None:
            ctx = Context(
                workflow=self._workflow,
                event_queue=event_queue,
            )
        else:
            # Use provided context but ensure it has the event queue
            ctx._event_queue = event_queue

        # Enqueue initial events
        if isinstance(start_events, StartEvent):
            start_events = [start_events]

        for event in start_events:
            await event_queue.put(event)

        # Process event queue
        iteration_count = 0
        result: Any = None

        try:
            while self._max_iterations == 0 or iteration_count < self._max_iterations:
                try:
                    # Get next event with timeout
                    event = await asyncio.wait_for(
                        event_queue.get(),
                        timeout=self._queue_wait_timeout,
                    )
                except asyncio.TimeoutError:
                    # Queue is empty - check for deadlock before completing
                    self._check_for_deadlock(ctx)
                    break

                # Check for StopEvent
                if isinstance(event, StopEvent):
                    result = event.result
                    break

                # Check buffer size periodically
                self._check_buffer_size()

                # Process the event
                await self._process_event(event, ctx)

                iteration_count += 1

            # Check if max iterations reached (only if not unlimited)
            if self._max_iterations > 0 and iteration_count >= self._max_iterations:
                raise WorkflowRuntimeError(
                    f"Execution workflow maximum iterations: ({self._max_iterations})."
                )

        except WorkflowRuntimeError:
            # Re-raise specific workflow exceptions without wrapping
            raise
        except Exception as e:
            raise WorkflowRuntimeError(f"Execution failure in workflow: {e!s}.")

        # Return workflow result
        return WorkflowResult(
            run_id=run_id,
            num_iterations=iteration_count,
            status=WorkflowStatus.COMPLETED,
            result=result,
        )

    async def _process_event(
        self,
        event: Event,
        context: Context,
    ) -> None:
        """
        Process a single event by dispatching to matching step methods.

        This method finds all step methods that listen to the event type and
        executes them. Single-event steps are executed immediately in parallel.
        Join steps buffer events and execute when all required events
        are collected (fan-in pattern).

        Args:
            event: The Event to process.
            context: The Context for step execution.

        Note:
            Steps are executed in parallel (fan-out pattern) when multiple
            steps listen to the same event type. Join steps use
            event buffering to coordinate execution.
        """
        event_type = type(event)

        # Find matching step methods
        matching_steps = self._workflow.get_steps_for_event(event)

        if not matching_steps:
            return

        # Process all matching steps - track step info with tasks
        task_info = []

        for step_name, step_method in matching_steps:
            is_join_step = step_name in self._workflow._join_step_registry

            # Handle join steps with event buffering
            if is_join_step:
                try:
                    await self._event_buffer.add_event(step_name, event)
                except Exception as e:
                    raise WorkflowRuntimeError(
                        f"Failed to buffer event {event_type.__name__} for step '{step_name}': {e!s}"
                    ) from e

                required_events = self._workflow._join_step_registry[step_name]
                events_dict = await self._event_buffer.get_events(
                    step_name, required_events
                )

                # If not all events are present yet, skip this step
                if events_dict is None:
                    continue

                event_or_events = events_dict
            else:
                # Single-event step - use event directly
                event_or_events = event

            # Get timeout and retry configuration from step metadata
            step_timeout = get_step_timeout(step_method)
            max_retries = get_step_max_retries(step_method)
            retry_delay = get_step_retry_delay(step_method)

            # Execute step with unified retry logic
            task = self._execute_with_retry(
                step_name,
                step_method,
                self._workflow,
                context,
                event_or_events,
                step_timeout,
                max_retries,
                retry_delay,
                is_join_step=is_join_step,
            )
            task_info.append((step_name, task))

        # Execute all tasks in parallel
        if not task_info:
            return

        # Gather results with exception handling
        results = await asyncio.gather(
            *[task for _, task in task_info], return_exceptions=True
        )

        # Process results and handle exceptions - direct matching with task_info
        for (step_name, _), result in zip(task_info, results):
            if result is not None:
                if isinstance(result, Event):
                    # Step returned an event, emit it
                    await context.emit(result)
                elif isinstance(result, Exception):
                    # Re-raise specific exception types without wrapping
                    if isinstance(result, WorkflowRuntimeError):
                        raise result
                    # Wrap other exceptions
                    raise WorkflowRuntimeError(
                        f"Execution failure in workflow step '{step_name}'. {result!s}"
                    )
                else:
                    raise WorkflowRuntimeError(
                        f"Step '{step_name}' expected Event, got {type(result).__name__}. "
                        "Steps must return a single Event or None."
                    )

    async def _execute_with_retry(
        self,
        step_name: str,
        step_method: Any,
        workflow: Any,
        context: Context,
        event_or_events: Event | dict[type, Event],
        timeout: float | None,
        max_retries: int,
        retry_delay: float,
        is_join_step: bool = False,
    ) -> Event | None:
        """
        Execute a step with timeout and retry logic.

        Handles both single-event and join steps with unified
        retry logic. Will retry execution on any exception (including timeout)
        up to `max_retries` times, with retry_delay seconds between attempts.

        Args:
            step_name: Name of the step (for error messages and buffer management).
            step_method: The step method to execute.
            workflow: The workflow instance.
            context: The Context for step execution.
            event_or_events: Single Event or dict of event types to Event instances.
            timeout: Optional timeout in seconds for step execution.
            max_retries: Number of retry attempts on failure.
            retry_delay: Delay in seconds between retry attempts.
            is_join_step: Whether this is a join step.

        Returns:
            Event returned by step, or None.

        Raises:
            WorkflowTimeoutError: If step execution times out after all retries.
            Exception: Any exception raised by single-event step after all retries.
        """
        for attempt in range(max_retries + 1):
            try:
                # Execute step with or without timeout
                if timeout is not None:
                    result = await asyncio.wait_for(
                        self._pool.execute(
                            step_method, workflow, context, event_or_events
                        ),
                        timeout=timeout,
                    )
                else:
                    result = await self._pool.execute(
                        step_method, workflow, context, event_or_events
                    )

                # Clear buffer after successful join step execution
                if is_join_step:
                    await self._event_buffer.clear_events(step_name)

                return result

            except asyncio.TimeoutError as e:
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue

                # Clear buffer on failure for join steps
                if is_join_step:
                    await self._event_buffer.clear_events(step_name)

                # All retries exhausted - build appropriate error message
                if is_join_step:
                    required_events = self._workflow._join_step_registry.get(
                        step_name, set()
                    )
                    event_names = [et.__name__ for et in required_events]
                    raise WorkflowTimeoutError(
                        f"Join step '{step_name}' execution timeout after {timeout}s "
                        f"(attempted {attempt + 1} times). "
                        f"Required events: {event_names}"
                    ) from e
                else:
                    raise WorkflowTimeoutError(
                        f"Step '{step_name}' execution timeout after {timeout}s "
                        f"(attempted {attempt + 1} times)"
                    ) from e

            except Exception as e:
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue

                # Clear buffer on failure for join steps
                if is_join_step:
                    await self._event_buffer.clear_events(step_name)

                # All retries exhausted - raise appropriate exception
                if is_join_step:
                    required_events = self._workflow._join_step_registry.get(
                        step_name, set()
                    )
                    event_names = [et.__name__ for et in required_events]
                    raise WorkflowRuntimeError(
                        f"Join step '{step_name}' failed: {e!s}\n"
                        f"Required events: {event_names}\n"
                        f"Attempt {attempt + 1}/{max_retries + 1}"
                    ) from e
                else:
                    raise

        return None

    def _check_buffer_size(self) -> None:
        """
        Check if event buffer size exceeds threshold.

        This method monitors the event buffer to detect potential issues
        like deadlocks or missing events that cause events to accumulate
        without being processed.

        Raises:
            WorkflowRuntimeError: If buffer size exceeds MAX_BUFFER_SIZE
        """
        size = self._event_buffer.get_buffer_size()
        if size > self._max_buffer_size:
            pending_steps = self._event_buffer.get_pending_steps()
            raise WorkflowRuntimeError(
                f"Event buffer size ({size}) exceeds maximum ({self._max_buffer_size}). "
                f"This may indicate a deadlock or missing events. "
                f"Steps with pending events: {', '.join(pending_steps)}"
            )

    def _check_for_deadlock(self, ctx: Context) -> None:
        """
        Check if workflow is deadlocked waiting for events.

        A deadlock occurs when:
        - Event queue is empty
        - Event buffer has pending events
        - No steps can execute

        This indicates that join steps are waiting for events that
        will never arrive, preventing workflow completion.

        Args:
            ctx: The workflow context

        Raises:
            WorkflowRuntimeError: If deadlock is detected
        """
        if ctx._event_queue.empty():
            buffer_size = self._event_buffer.get_buffer_size()
            if buffer_size > 0:
                # Get details of pending events for error message
                pending_steps = self._event_buffer.get_pending_steps()

                # Build detailed error message with step status
                details = []
                for step_name in pending_steps:
                    status = self._event_buffer.get_step_status(step_name)
                    required_events = self._workflow._join_step_registry.get(
                        step_name, set()
                    )
                    required_names = [et.__name__ for et in required_events]
                    received_names = list(status.keys())
                    missing_names = [
                        name for name in required_names if name not in received_names
                    ]

                    details.append(
                        f"  - '{step_name}': received {received_names}, "
                        f"missing {missing_names}"
                    )

                raise WorkflowRuntimeError(
                    f"Workflow deadlock detected: {buffer_size} events buffered "
                    f"but no steps can execute. Check for missing event emissions.\n"
                    f"Pending steps:\n" + "\n".join(details)
                )
