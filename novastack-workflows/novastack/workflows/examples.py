"""
Workflow framework examples using copy-on-write state management.

This module demonstrates various workflow patterns using the redesigned
event-driven workflow system with StateStore and copy-on-write semantics.

Examples:
    1. Simple Workflow: Basic event chaining without state
    2. Workflow with State Management: Demonstrates copy-on-write state mutations
    3. Parallel Fan-Out Workflow: Multiple steps with thread-safe state
    4. Dynamic Event Emission: Manual event emission with state tracking
    5. Workflow Composition: Sub-workflows with shared state store
    6. Timeout and Retry Features: Resilient workflows with state management
    7. State Persistence Across Multiple Runs: Demonstrates state persistence with context reuse

Each example includes a test function that can be run independently.
"""

import asyncio
import random
from typing import Any

from pydantic import BaseModel, Field
from novastack.workflows import (
    Workflow,
    Context,
    step,
    Event,
    StartEvent,
    StopEvent,
)
from novastack.workflows.exceptions import WorkflowTimeoutError, WorkflowRuntimeError
from novastack.workflows.enums import WorkflowStatus


# =============================================================================
# Example 1: Simple Workflow (Basic Test)
# =============================================================================


class MyEvent(Event):
    """Custom event with message."""

    message: str


class SimpleWorkflow(Workflow):
    """
    Simple workflow demonstrating basic event chaining.

    This workflow shows:
    - Workflow without state management
    - Simple event chaining: StartEvent → MyEvent → StopEvent
    - Basic decorator usage with @step(on=...)
    - Returning events from step methods
    """

    @step(on=StartEvent)
    async def start(self, ctx: Context, ev: StartEvent) -> MyEvent:
        """
        Process start event and emit custom event.

        This step receives the StartEvent with input_msg and transforms
        it into a MyEvent for the next step to process.
        """
        input_msg = ev.get("input_msg", "")
        return MyEvent(message=f"Processed: {input_msg}")

    @step(on=MyEvent)
    async def process(self, ctx: Context, ev: MyEvent) -> StopEvent:
        """
        Process custom event and complete workflow.

        This step receives MyEvent and returns StopEvent to complete
        the workflow execution.
        """
        return StopEvent(result=ev.message)


async def test_simple_workflow():
    """Test simple workflow execution."""
    print("\n" + "=" * 80)
    print("Example 1: Simple Workflow")
    print("=" * 80)
    print("Demonstrates: Basic event chaining without state")
    print()

    workflow = SimpleWorkflow()
    result = await workflow.run(input_msg="Hello, World!")

    print(f"Input: 'Hello, World!'")
    print(f"Result: {result}")

    assert result == "Processed: Hello, World!"
    print("✓ Simple workflow test passed")


# =============================================================================
# Example 2: State Management with Copy-on-Write
# =============================================================================


class IncrementEvent(Event):
    """Event to trigger increment operation."""

    value: int


class RunState(BaseModel):
    """State model for workflow state management."""

    counter: int = Field(default=0, description="Counter value")
    items: list[str] = Field(default_factory=list, description="List of items")
    total: int = Field(default=0, description="Total sum")


class StateWorkflow(Workflow):
    """
    Workflow demonstrating copy-on-write state management with auto-initialization.

    This workflow shows:
    - Automatic state initialization using DictLikeModel (no manual setup needed!)
    - Copy-on-write state mutations with async context manager
    - Immutability by default
    - Thread-safe state updates
    - Automatic rollback on errors
    - Explicit mutation contexts
    """

    @step(on=StartEvent)
    async def initialize(self, ctx: Context[RunState], ev: StartEvent) -> IncrementEvent:
        """
        Initialize workflow state using copy-on-write.

        State is automatically initialized as RunState() - no manual setup needed!
        RunState provides type-safe field access with validation.
        
        Demonstrates explicit state mutation through context manager.
        Changes are isolated until committed on context exit.
        """
        # State is already initialized automatically with RunState!
        # No need for: if ctx.state is None: ctx._store._state = RunState()
        
        async with ctx.store.edit_state() as state:
            state.counter = 0
            state.items = ["initialized"]
            state.total = 0

        return IncrementEvent(value=5)

    @step(on=IncrementEvent)
    async def increment(self, ctx: Context[RunState], ev: IncrementEvent) -> StopEvent:
        """
        Increment counter and update state with copy-on-write.

        Demonstrates copy-on-write semantics for state mutations.
        All changes are atomic and thread-safe.
        """
        # Copy-on-write mutation
        async with ctx.store.edit_state() as state:
            state.counter += ev.value
            state.items.append(f"incremented by {ev.value}")
            state.total = state.counter * 2

        # Read-only access (no copy needed)
        return StopEvent(
            result={
                "counter": ctx.state.counter,
                "items": ctx.state.items,
                "total": ctx.state.total,
            }
        )


async def test_state_workflow():
    """Test workflow with copy-on-write state management."""
    print("\n" + "=" * 80)
    print("Example 2: State Management with Copy-on-Write")
    print("=" * 80)
    print("Demonstrates: Immutable state with explicit mutation contexts")
    print()

    workflow = StateWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx)

    print(f"Counter: {result['counter']}")
    print(f"Items: {result['items']}")
    print(f"Total: {result['total']}")

    assert result["counter"] == 5
    assert result["items"] == ["initialized", "incremented by 5"]
    assert result["total"] == 10
    print("✓ Copy-on-write state workflow test passed")


# =============================================================================
# Example 3: Parallel Fan-Out Workflow
# =============================================================================


class DataFetchedEvent(Event):
    """Event emitted when data is fetched."""

    data_id: int


class ProcessedEvent(Event):
    """Event emitted when processing is complete."""

    processor: str
    result: Any


class ParallelState(BaseModel):
    """State for parallel workflow."""

    results: list[dict[str, Any]] = Field(default_factory=list)
    completed_count: int = Field(default=0)


class ParallelWorkflow(Workflow):
    """
    Workflow demonstrating parallel execution with copy-on-write state.

    This workflow shows:
    - Multiple steps listening to the same event
    - Parallel execution (fan-out pattern)
    - Thread-safe state coordination with copy-on-write
    - Natural parallelism with immutable state
    """

    @step(on=StartEvent)
    async def fetch_data(self, ctx: Context, ev: StartEvent) -> DataFetchedEvent:
        """
        Fetch data and trigger parallel processing.

        This single event will trigger both process_a and process_b
        to execute in parallel.
        """
        # Initialize state if not present
        if ctx.state is None:
            ctx._store._state = ParallelState()

        # Initialize state with copy-on-write
        async with ctx.store.edit_state() as state:
            state.results = []
            state.completed_count = 0

        data_id = ev.get("data_id", 1)
        return DataFetchedEvent(data_id=data_id)

    @step(on=DataFetchedEvent)
    async def process_a(self, ctx: Context, ev: DataFetchedEvent) -> ProcessedEvent:
        """
        Process data in parallel (processor A).

        This step runs in parallel with process_b when DataFetchedEvent
        is emitted.
        """
        # Simulate processing
        result = f"Processed by A: {ev.data_id * 2}"
        return ProcessedEvent(processor="A", result=result)

    @step(on=DataFetchedEvent)
    async def process_b(self, ctx: Context, ev: DataFetchedEvent) -> ProcessedEvent:
        """
        Process data in parallel (processor B).

        This step runs in parallel with process_a when DataFetchedEvent
        is emitted.
        """
        # Simulate processing
        result = f"Processed by B: {ev.data_id * 3}"
        return ProcessedEvent(processor="B", result=result)

    @step(on=ProcessedEvent)
    async def collect_results(
        self, ctx: Context, ev: ProcessedEvent
    ) -> StopEvent | None:
        """
        Collect results from parallel processors.

        This step is called once for each ProcessedEvent. It tracks
        completion and emits StopEvent when all parallel steps finish.
        Thread-safe thanks to copy-on-write semantics.
        """
        # Thread-safe copy-on-write mutation
        async with ctx.store.edit_state() as state:
            state.results.append(
                {
                    "processor": ev.processor,
                    "result": ev.result,
                }
            )
            state.completed_count += 1

        # Check if both parallel steps completed (read-only access)
        if ctx.state.completed_count >= 2:
            return StopEvent(result=ctx.state.results)

        return None  # Wait for more results


async def test_parallel_workflow():
    """Test parallel fan-out workflow."""
    print("\n" + "=" * 80)
    print("Example 3: Parallel Fan-Out Workflow")
    print("=" * 80)
    print("Demonstrates: Multiple steps with thread-safe copy-on-write state")
    print()

    workflow = ParallelWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx, data_id=10)

    print(f"Parallel processing results:")
    for item in result:
        print(f"  - {item['processor']}: {item['result']}")

    assert len(result) == 2
    assert any(r["processor"] == "A" for r in result)
    assert any(r["processor"] == "B" for r in result)
    print("✓ Parallel workflow test passed")


# =============================================================================
# Example 4: Dynamic Event Emission
# =============================================================================


class TaskEvent(Event):
    """Event for individual task processing."""

    task_id: int
    data: str


class TaskCompleteEvent(Event):
    """Event emitted when a task completes."""

    task_id: int
    result: str


class DynamicState(BaseModel):
    """State for dynamic workflow."""

    total_tasks: int = Field(default=0)
    completed_tasks: int = Field(default=0)
    results: list[dict[str, Any]] = Field(default_factory=list)


class DynamicWorkflow(Workflow):
    """
    Workflow demonstrating dynamic event emission with copy-on-write state.

    This workflow shows:
    - Using ctx.emit() for manual event emission
    - Multiple events emitted from a single step
    - Copy-on-write state for tracking
    - Flexible event patterns with immutable state
    """

    @step(on=StartEvent)
    async def split_tasks(self, ctx: Context, ev: StartEvent) -> None:
        """
        Split work into multiple tasks and emit events dynamically.

        This step demonstrates ctx.emit() for manual event emission.
        The number of events depends on runtime data.
        """
        # Initialize state if not present
        if ctx.state is None:
            ctx._store._state = DynamicState()

        tasks = [
            {"id": 1, "data": "Task A"},
            {"id": 2, "data": "Task B"},
            {"id": 3, "data": "Task C"},
        ]

        # Initialize state with copy-on-write
        async with ctx.store.edit_state() as state:
            state.total_tasks = len(tasks)
            state.completed_tasks = 0
            state.results = []

        # Emit an event for each task using ctx.emit()
        for task in tasks:
            await ctx.emit(TaskEvent(task_id=task["id"], data=task["data"]))

    @step(on=TaskEvent)
    async def process_task(self, ctx: Context, ev: TaskEvent) -> TaskCompleteEvent:
        """
        Process individual tasks emitted dynamically.

        Multiple instances of this step execute in parallel,
        one for each TaskEvent emitted.
        """
        # Process task
        result = ev.data.upper()
        return TaskCompleteEvent(task_id=ev.task_id, result=result)

    @step(on=TaskCompleteEvent)
    async def collect_task_results(
        self, ctx: Context, ev: TaskCompleteEvent
    ) -> StopEvent | None:
        """
        Collect results from dynamically processed tasks.

        Tracks completion and emits StopEvent when all tasks finish.
        Thread-safe with copy-on-write semantics.
        """
        # Thread-safe copy-on-write mutation
        async with ctx.store.edit_state() as state:
            state.results.append(
                {
                    "task_id": ev.task_id,
                    "result": ev.result,
                }
            )
            state.completed_tasks += 1

        # Check if all tasks completed (read-only access)
        if ctx.state.completed_tasks >= ctx.state.total_tasks:
            # Sort results by task_id for consistent output
            sorted_results = sorted(ctx.state.results, key=lambda x: x["task_id"])
            return StopEvent(result=sorted_results)

        return None  # Wait for more tasks


async def test_dynamic_emission():
    """Test dynamic event emission workflow."""
    print("\n" + "=" * 80)
    print("Example 4: Dynamic Event Emission")
    print("=" * 80)
    print("Demonstrates: Using ctx.emit() with copy-on-write state")
    print()

    workflow = DynamicWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx)

    print(f"Completed {len(result)} tasks:")
    for item in result:
        print(f"  - Task {item['task_id']}: {item['result']}")

    assert len(result) == 3
    assert result[0]["result"] == "TASK A"
    assert result[1]["result"] == "TASK B"
    assert result[2]["result"] == "TASK C"
    print("✓ Dynamic emission workflow test passed")


# =============================================================================
# Example 5: Workflow Composition (Sub-workflows)
# =============================================================================


class DataCleanEvent(Event):
    """Event with raw data to clean."""

    raw_data: str


class DataValidateEvent(Event):
    """Event with cleaned data to validate."""

    cleaned_data: str


class DataTransformEvent(Event):
    """Event with validated data to transform."""

    validated_data: str


class PipelineState(BaseModel):
    """State for pipeline workflow."""

    cleaning_done: bool = Field(default=False)
    validation_done: bool = Field(default=False)


# Sub-workflow 1: Data Cleaning
class DataCleaningWorkflow(Workflow):
    """
    Sub-workflow for data cleaning operations.

    This workflow demonstrates:
    - Reusable workflow component
    - Isolated state (independent from parent)
    - Clean separation of concerns
    """

    @step(on=StartEvent)
    async def clean(self, ctx: Context, ev: StartEvent) -> DataCleanEvent:
        """Clean the input data."""
        raw = ev.input_msg
        cleaned = raw.strip().lower()

        return DataCleanEvent(raw_data=cleaned)

    @step(on=DataCleanEvent)
    async def finish_cleaning(self, ctx: Context, ev: DataCleanEvent) -> StopEvent:
        """Finish cleaning workflow."""
        return StopEvent(result=ev.raw_data)


# Sub-workflow 2: Data Validation
class DataValidationWorkflow(Workflow):
    """
    Sub-workflow for data validation operations.

    This workflow demonstrates:
    - Reusable validation logic
    - Error handling in sub-workflows
    - Isolated state (independent from parent)
    """

    @step(on=StartEvent)
    async def validate(self, ctx: Context, ev: StartEvent) -> DataValidateEvent:
        """Validate the input data."""
        data = ev.input_msg
        # Simple validation: check if not empty
        if not data:
            raise ValueError("Data cannot be empty")

        return DataValidateEvent(cleaned_data=data)

    @step(on=DataValidateEvent)
    async def finish_validation(self, ctx: Context, ev: DataValidateEvent) -> StopEvent:
        """Finish validation workflow."""
        return StopEvent(result=ev.cleaned_data)


# Main workflow: Orchestrates sub-workflows
class DataPipelineWorkflow(Workflow):
    """
    Main workflow that orchestrates sub-workflows.

    This workflow demonstrates:
    - Simple sub-workflow execution via direct run() calls
    - Complete context isolation (each sub-workflow is independent)
    - No automatic state sharing between workflows
    - Explicit communication via parameters and return values
    - Modular and reusable workflow design
    - Sub-workflows can be nested (sub-sub-workflows)
    """

    @step(on=StartEvent)
    async def start_pipeline(self, ctx: Context, ev: StartEvent) -> DataTransformEvent:
        """Orchestrate data processing pipeline using sub-workflows."""
        # Initialize parent workflow state
        if ctx.state is None:
            ctx._store._state = PipelineState()

        # Step 1: Clean data using sub-workflow (isolated context)
        # Simply create and run the sub-workflow directly
        cleaning_workflow = DataCleaningWorkflow()
        clean_result = await cleaning_workflow.run(input_msg=ev.input_msg)

        # Update parent state after sub-workflow completes
        async with ctx.store.edit_state() as state:
            state.cleaning_done = True

        # Step 2: Validate cleaned data using sub-workflow (isolated context)
        # Each sub-workflow execution is completely independent
        validation_workflow = DataValidationWorkflow()
        validate_result = await validation_workflow.run(input_msg=clean_result)

        # Update parent state after sub-workflow completes
        async with ctx.store.edit_state() as state:
            state.validation_done = True

        # Step 3: Transform in main workflow
        transformed = validate_result.upper()

        return DataTransformEvent(validated_data=transformed)

    @step(on=DataTransformEvent)
    async def finish_pipeline(self, ctx: Context, ev: DataTransformEvent) -> StopEvent:
        """Finish the pipeline."""
        # Verify parent workflow state (sub-workflows don't affect this)
        assert ctx.state.cleaning_done is True
        assert ctx.state.validation_done is True

        return StopEvent(result=ev.validated_data)


async def test_workflow_composition():
    """Test workflow composition with sub-workflows."""
    print("\n" + "=" * 80)
    print("Example 5: Workflow Composition (Sub-workflows)")
    print("=" * 80)
    print("Demonstrates: Simple sub-workflow execution via direct run() calls")
    print("Each sub-workflow has completely isolated context and state")
    print("Communication happens explicitly via parameters and return values")
    print()

    workflow = DataPipelineWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx, input_msg="  Hello World  ")

    print(f"Input: '  Hello World  '")
    print(f"After cleaning (sub-workflow): 'hello world'")
    print(f"After validation (sub-workflow): 'hello world'")
    print(f"After transformation (main workflow): '{result}'")
    print(f"\nNote: Each run() call creates an independent execution")
    print(f"No automatic context sharing - communication is explicit")

    assert result == "HELLO WORLD"
    print("✓ Workflow composition test passed")


# =============================================================================
# Example 6: Timeout and Retry Features
# =============================================================================


class ApiCallEvent(Event):
    """Event to trigger API call."""

    endpoint: str


class ApiResponseEvent(Event):
    """Event with API response."""

    data: str
    attempts: int


class ApiProcessedEvent(Event):
    """Event with processed API data."""

    result: str


class ApiState(BaseModel):
    """State for API workflow."""

    start_time: float = Field(default=0.0)
    api_attempts: int = Field(default=0)


class ResilientApiWorkflow(Workflow):
    """
    Workflow demonstrating timeout and retry features with copy-on-write state.

    Features demonstrated:
    - Step timeout (5 seconds max)
    - Automatic retry (up to 3 attempts)
    - 1 second delay between retries
    - Error handling for timeout and retry exhaustion
    - Thread-safe state tracking with copy-on-write
    """

    @step(on=StartEvent)
    async def start(self, ctx: Context[ApiState], ev: StartEvent) -> ApiCallEvent:
        """Start the workflow."""

        async with ctx.store.edit_state() as state:
            state.start_time = asyncio.get_event_loop().time()

        return ApiCallEvent(endpoint=ev.input_msg)

    @step(
        on=ApiCallEvent,
        timeout=5.0,  # 5 second timeout
        num_retries=3,  # Retry up to 3 times
        retry_delay=1.0,  # 1 second delay between retries
    )
    async def call_flaky_api(self, ctx: Context[ApiState], ev: ApiCallEvent) -> ApiResponseEvent:
        """
        Simulate a flaky API call that might fail or timeout.

        This step demonstrates:
        - Automatic retry on failure
        - Timeout protection
        - Tracking retry attempts with copy-on-write
        """
        # Read current attempts (read-only)
        attempt = ctx.state.api_attempts + 1

        # Update attempts with copy-on-write
        async with ctx.store.edit_state() as state:
            state.api_attempts = attempt

        print(f"  → API call attempt {attempt} to {ev.endpoint}")

        # Simulate random failures (50% chance)
        if random.random() < 0.5 and attempt < 3:
            print(f"  ✗ API call failed (attempt {attempt})")
            raise Exception(f"API temporarily unavailable (attempt {attempt})")

        # Simulate API delay
        await asyncio.sleep(0.2)

        print(f"  ✓ API call succeeded (attempt {attempt})")
        return ApiResponseEvent(data=f"Response from {ev.endpoint}", attempts=attempt)

    @step(on=ApiResponseEvent, timeout=2.0)
    async def process_response(
        self, ctx: Context[ApiState], ev: ApiResponseEvent
    ) -> ApiProcessedEvent:
        """
        Process the API response with timeout protection.

        This step demonstrates:
        - Simple timeout without retry
        - Fast processing requirement
        """
        print(f"  → Processing response (took {ev.attempts} attempts)")

        # Simulate processing
        await asyncio.sleep(0.1)

        processed = ev.data.upper()
        return ApiProcessedEvent(result=processed)

    @step(on=ApiProcessedEvent)
    async def finish(self, ctx: Context[ApiState], ev: ApiProcessedEvent) -> StopEvent:
        """Finish the workflow."""
        # Read-only access to state
        elapsed = asyncio.get_event_loop().time() - ctx.state.start_time
        total_attempts = ctx.state.api_attempts

        result = {
            "result": ev.result,
            "total_attempts": total_attempts,
            "elapsed_time": f"{elapsed:.2f}s",
        }

        return StopEvent(result=result)


async def test_timeout_retry_workflow():
    """Test workflow with timeout and retry features."""
    print("\n" + "=" * 80)
    print("Example 6: Timeout and Retry Features")
    print("=" * 80)
    print("Demonstrates: Resilient API calls with copy-on-write state tracking")
    print()

    workflow = ResilientApiWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx, input_msg="/api/data")

    print(f"\n✓ Workflow completed successfully!")
    print(f"  Result: {result['result']}")
    print(f"  Total attempts: {result['total_attempts']}")
    print(f"  Elapsed time: {result['elapsed_time']}")

    assert result["total_attempts"] >= 1
    print("✓ Timeout and retry workflow test passed")


# =============================================================================
# Example 7: State Persistence Across Multiple Runs
# =============================================================================


class CounterState(BaseModel):
    """State model for counter workflow."""

    counter: int = Field(default=0, description="Counter value")
    run_count: int = Field(default=0, description="Number of runs")


class CounterWorkflow(Workflow):
    """
    Workflow demonstrating state persistence across multiple runs.

    This workflow shows:
    - State persists when the same context is reused
    - Multiple workflow executions with the same context
    - Counter incrementing across runs
    - Clear demonstration of context reuse behavior

    Key Insight:
    When you create a Context and pass it to multiple workflow.run() calls,
    the state persists between runs. This is useful for:
    - Maintaining session state
    - Accumulating results across multiple operations
    - Building stateful workflows that remember previous executions
    """

    @step(on=StartEvent)
    async def increment_counter(self, ctx: Context[CounterState], ev: StartEvent) -> StopEvent:
        """
        Increment counter and track run count.

        This step demonstrates:
        - Automatic state initialization from Context[CounterState] annotation
        - Reading and updating state with copy-on-write
        - State persisting across multiple workflow executions
        """
        # Read current values (read-only access)
        current_counter = ctx.state.counter
        current_run_count = ctx.state.run_count

        # Increment with copy-on-write
        async with ctx.store.edit_state() as state:
            state.counter = current_counter + 1
            state.run_count = current_run_count + 1

        # Get increment value from event or use default
        increment_by = ev.get("increment_by", 1)

        print(
            f"  Run #{ctx.state.run_count}: Counter = {ctx.state.counter} (incremented by {increment_by})"
        )

        return StopEvent(
            result={
                "counter": ctx.state.counter,
                "run_count": ctx.state.run_count,
            }
        )


async def test_state_persistence():
    """Test state persistence across multiple workflow runs."""
    print("\n" + "=" * 80)
    print("Example 7: State Persistence Across Multiple Runs")
    print("=" * 80)
    print("Demonstrates: State persists when the same context is reused")
    print()

    workflow = CounterWorkflow()

    # Create a single context that will be reused
    ctx = Context(workflow)

    print("Creating a single context and running workflow multiple times...")
    print()

    # Run 1: Counter should be 1
    result1 = await workflow.run(ctx=ctx)
    assert result1["counter"] == 1
    assert result1["run_count"] == 1

    # Run 2: Counter should be 2 (state persisted!)
    result2 = await workflow.run(ctx=ctx)
    assert result2["counter"] == 2
    assert result2["run_count"] == 2

    # Run 3: Counter should be 3 (state persisted!)
    result3 = await workflow.run(ctx=ctx)
    assert result3["counter"] == 3
    assert result3["run_count"] == 3

    # Run 4: Counter should be 4 (state persisted!)
    result4 = await workflow.run(ctx=ctx)
    assert result4["counter"] == 4
    assert result4["run_count"] == 4

    print()
    print(f"✓ Final state after 4 runs:")
    print(f"  Counter: {result4['counter']}")
    print(f"  Total runs: {result4['run_count']}")
    print()
    print("Key Takeaway: The same context preserves state across multiple runs!")
    print("This is different from creating a new context for each run.")
    print()

    # Demonstrate contrast: new context = fresh state
    print("Contrast: Creating a NEW context for comparison...")
    new_ctx = Context(workflow)
    result_new = await workflow.run(ctx=new_ctx)
    print(f"  New context run: Counter = {result_new['counter']} (starts fresh!)")
    print()

    assert result_new["counter"] == 1  # Fresh start with new context
    assert result_new["run_count"] == 1

    print("✓ State persistence workflow test passed")


# =============================================================================
# Example 8: Generic State with DictLikeModel (No Type Annotation)
# =============================================================================


class GenericStateWorkflow(Workflow):
    """
    Workflow demonstrating automatic state initialization with DictLikeModel.
    
    When no Context[StateType] is specified, DictLikeModel is used by default,
    allowing dynamic field assignment like a dictionary.
    """

    @step(on=StartEvent)
    async def start(self, ctx: Context, ev: StartEvent) -> StopEvent:
        """
        Use state without explicit type - DictLikeModel allows dynamic fields.
        
        State is automatically initialized as DictLikeModel() on first access.
        """
        # State is already initialized with DictLikeModel!
        async with ctx.store.edit_state() as state:
            state.counter = 1
            state.message = "Hello from generic state"
            state.items = ["a", "b", "c"]
        
        return StopEvent(
            result={
                "counter": ctx.state.counter,
                "message": ctx.state.message,
                "items": ctx.state.items,
            }
        )


async def test_generic_state_workflow():
    """Test workflow with generic DictLikeModel state."""
    print("\n" + "=" * 80)
    print("Example 8: Generic State with DictLikeModel")
    print("=" * 80)
    print("Demonstrates: Auto-initialization with dynamic fields (no type annotation)")
    print()

    workflow = GenericStateWorkflow()
    result = await workflow.run(input_msg="test")

    print(f"Counter: {result['counter']}")
    print(f"Message: {result['message']}")
    print(f"Items: {result['items']}")
    
    assert result["counter"] == 1
    assert result["message"] == "Hello from generic state"
    assert result["items"] == ["a", "b", "c"]
    
    print("✓ Generic state workflow test passed")



# =============================================================================
# Example 9: State Type Consistency Validation
# =============================================================================


# This workflow is commented out because it will raise WorkflowValidationError
# at class definition time! Uncomment to test the validation:
#
# class InconsistentStateWorkflow(Workflow):
#     """
#     This workflow demonstrates state type consistency validation.
#
#     The workflow framework validates that all steps use the same Context[StateType].
#     This example intentionally uses different state types to show the validation error.
#     """
#
#     @step(on=StartEvent)
#     async def start(self, ctx: Context[RunState], ev: StartEvent) -> MyEvent:
#         """First step uses Context[RunState]."""
#         return MyEvent(message="test")
#
#     @step(on=MyEvent)
#     async def process(self, ctx: Context[ParallelState], ev: MyEvent) -> StopEvent:
#         """
#         Second step uses Context[ParallelState].
#
#         ❌ This will raise WorkflowValidationError!
#         All steps must use the same Context[StateType].
#         """
#         return StopEvent(result="done")


async def test_state_type_consistency():
    """
    Test state type consistency validation.
    
    This test demonstrates that the workflow framework validates state type
    consistency across all steps. When steps use different state types,
    a WorkflowValidationError is raised at class definition time.
    """
    print("\n" + "=" * 80)
    print("Example 9: State Type Consistency Validation")
    print("=" * 80)
    print("Demonstrates: Validation of consistent state types across workflow steps")
    print()
    
    print("⚠️  Note: The InconsistentStateWorkflow class is commented out because")
    print("    it would raise WorkflowValidationError at class definition time.")
    print()
    print("Expected behavior:")
    print("  - All steps in a workflow must use the same Context[StateType]")
    print("  - Using Context[RunState] in one step and Context[ParallelState]")
    print("    in another will raise WorkflowValidationError")
    print("  - This validation happens when the class is defined, not at runtime")
    print()
    print("To test this validation:")
    print("  1. Uncomment the InconsistentStateWorkflow class definition")
    print("  2. Run the examples again")
    print("  3. Observe the WorkflowValidationError with details about the inconsistency")
    print()
    print("✓ State type consistency validation example completed")


# =============================================================================
# Main Example Runner
# =============================================================================


async def main():
    """
    Run all workflow examples.

    This function executes all example workflows in sequence,
    demonstrating the various features of the copy-on-write workflow system.

    Usage:
        python -m novastack.workflows.examples
    """
    print("\n" + "=" * 80)
    print("WORKFLOW FRAMEWORK EXAMPLES")
    print("=" * 80)
    print("Running all examples with copy-on-write state management...")

    try:
        await test_simple_workflow()
        await test_state_workflow()
        await test_parallel_workflow()
        await test_dynamic_emission()
        await test_workflow_composition()
        await test_timeout_retry_workflow()
        await test_state_persistence()
        await test_generic_state_workflow()
        await test_state_type_consistency()

        print("\n" + "=" * 80)
        print("✓ All examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

