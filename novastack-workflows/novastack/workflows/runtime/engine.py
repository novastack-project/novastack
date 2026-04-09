import asyncio
import uuid
from typing import Any, TYPE_CHECKING

from novastack.workflows.context import Context
from novastack.workflows.decorators import (
    get_step_timeout,
    get_step_num_retries,
    get_step_retry_delay,
)
from novastack.workflows.events import Event, StartEvent, StopEvent
from novastack.workflows.exceptions import (
    WorkflowRuntimeError,
    WorkflowTimeoutError,
    WorkflowValidationError,
)
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
    """

    def __init__(
        self,
        workflow: "Workflow",
        max_iterations: int = 1000,
        queue_wait_timeout: float = 1.0,
        max_workers: int = 100,
    ) -> None:
        if max_iterations < 0:
            raise WorkflowValidationError("'max_iterations' must be 0 (unlimited) or greater")
        if queue_wait_timeout <= 0:
            raise WorkflowValidationError("'queue_wait_timeout' must be greater than 0")

        self._workflow = workflow
        self._max_iterations = max_iterations
        self._queue_wait_timeout = queue_wait_timeout
        self._pool = StepExecutionPool(max_workers)

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
        iteration = 0
        result: Any = None

        try:
            while self._max_iterations == 0 or iteration < self._max_iterations:
                try:
                    # Get next event with timeout
                    event = await asyncio.wait_for(
                        event_queue.get(),
                        timeout=self._queue_wait_timeout,
                    )
                except asyncio.TimeoutError:
                    # Queue is empty, workflow complete
                    break

                # Check for StopEvent
                if isinstance(event, StopEvent):
                    result = event.result
                    break

                # Process the event
                await self._process_event(event, ctx)

                iteration += 1

            # Check if max iterations reached (only if not unlimited)
            if self._max_iterations > 0 and iteration >= self._max_iterations:
                raise WorkflowRuntimeError(f"Execution workflow maximum iterations: ({self._max_iterations}).")

        except WorkflowRuntimeError:
            raise
        except Exception as e:
            raise WorkflowRuntimeError(f"Execution failure in workflow: {str(e)}.")

        # Return workflow result
        return WorkflowResult(
            run_id=run_id,
            num_iterations=iteration,
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
        executes them in parallel using asyncio.gather. It handles exceptions
        and enqueues any events returned by the steps.

        Args:
            event: The Event to process.
            context: The Context for step execution.

        Note:
            Steps are executed in parallel (fan-out pattern) when multiple
            steps listen to the same event type.
        """
        # Find matching step methods
        matching_steps = self._workflow.get_steps_for_event(event)

        if not matching_steps:
            # No steps listen to this event, skip silently (same behavior as return None)
            return

        # Execute all matching steps in parallel with timeout and retry
        tasks = []
        for step_name, step_method in matching_steps:
            # Get timeout and retry configuration from step metadata
            step_timeout = get_step_timeout(step_method)
            num_retries = get_step_num_retries(step_method)
            retry_delay = get_step_retry_delay(step_method)

            # Execute step with retry logic
            task = self._execute_step_with_retry(
                step_method,
                self._workflow,
                context,
                event,
                step_timeout,
                num_retries,
                retry_delay,
            )
            tasks.append(task)

        # Gather results with exception handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        for i, result in enumerate(results):
            step_name, step_method = matching_steps[i]

            if result is None:
                pass
            elif isinstance(result, Event):
                # Step returned an event, emit it
                await context.emit(result)
            elif isinstance(result, Exception):
                raise WorkflowRuntimeError(f"Execution failure in workflow step '{step_name}'. "
                f"{str(result)}")
            else:
                raise WorkflowRuntimeError(
                    f"Step '{step_name}' expected Event, got {type(result).__name__}. "
                    "Steps must return a single Event or None."
                )

    async def _execute_step_with_retry(
        self,
        step_method: Any,
        workflow: Any,
        context: Context,
        event: Event,
        timeout: float | None,
        num_retries: int,
        retry_delay: float,
    ) -> Event | None:
        """
        Execute step with timeout and retry logic using execution pool.

        This method wraps step execution with configurable timeout and retry
        behavior. It will retry the step execution on any exception (including
        timeout) up to num_retries times, with retry_delay seconds between attempts.

        Args:
            step_method: The step method to execute.
            workflow: The workflow instance.
            context: The Context for step execution.
            event: The Event to process.
            timeout: Optional timeout in seconds for step execution.
            num_retries: Number of retry attempts on failure.
            retry_delay: Delay in seconds between retry attempts.
        """

        for attempt in range(num_retries + 1):
            try:
                if timeout is not None:
                    result = await asyncio.wait_for(
                        self._pool.execute(step_method, workflow, context, event),
                        timeout=timeout,
                    )
                else:
                    result = await self._pool.execute(
                        step_method, workflow, context, event
                    )

                return result

            except asyncio.TimeoutError as e:
                if attempt < num_retries:
                    await asyncio.sleep(retry_delay)
                    continue

                # All retries exhausted
                raise WorkflowTimeoutError(
                    f"Step execution timeout after {timeout}s "
                    f"(attempted {attempt + 1} times)"
                ) from e

            except Exception:
                if attempt < num_retries:
                    await asyncio.sleep(retry_delay)
                    continue
                
                # All retries exhausted
                raise

        return None
