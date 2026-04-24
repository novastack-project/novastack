import pytest
from novastack.workflows import Workflow
from novastack.workflows.context import Context
from novastack.workflows.decorators import step
from novastack.workflows.events import Event, StartEvent, StopEvent
from novastack.workflows.exceptions import (
    WorkflowRuntimeError,
    WorkflowValidationError,
)


class EventA(Event):
    """Test event A."""

    data: str = "a"


class EventB(Event):
    """Test event B."""

    data: str = "b"


class EventC(Event):
    """Test event C."""

    data: str = "c"


class EventD(Event):
    """Test event D."""

    data: str = "d"


# ============================================================================
# Part 1: Circular Dependency Detection Tests
# ============================================================================


def test_circular_dependency_direct():
    """Test that direct circular dependencies are detected."""
    with pytest.raises(WorkflowValidationError) as exc_info:

        class CircularWorkflow(Workflow):
            @step(depends_on=StartEvent)
            async def start(self, ctx: Context, ev: StartEvent) -> EventA:
                return EventA()

            @step(depends_on=[EventA, EventB])
            async def join_ab(self, ctx: Context, events: dict) -> EventC:
                return EventC()

            @step(depends_on=[EventC, EventD])
            async def join_cd(self, ctx: Context, events: dict) -> EventB:
                # This creates a cycle: join_ab needs EventB, join_cd produces EventB
                # but join_cd needs EventC which is produced by join_ab
                return EventB()

    assert "Circular dependency detected" in str(exc_info.value)
    assert "join_ab" in str(exc_info.value)
    assert "join_cd" in str(exc_info.value)


def test_no_circular_dependency_valid_chain():
    """Test that valid dependency chains don't raise errors."""

    # This should not raise any errors
    class ValidWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            return EventA()

        @step(depends_on=StartEvent)
        async def start2(self, ctx: Context, ev: StartEvent) -> EventB:
            return EventB()

        @step(depends_on=[EventA, EventB])
        async def join_ab(self, ctx: Context, events: dict) -> EventC:
            return EventC()

        @step(depends_on=EventC)
        async def process_c(self, ctx: Context, ev: EventC) -> StopEvent:
            return StopEvent(result="done")

    # If we get here without exception, the test passes
    assert ValidWorkflow is not None


def test_no_circular_dependency_parallel_branches():
    """Test that parallel branches without cycles are valid."""

    class ParallelWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            return EventA()

        @step(depends_on=EventA)
        async def branch1(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        @step(depends_on=EventA)
        async def branch2(self, ctx: Context, ev: EventA) -> EventC:
            return EventC()

        @step(depends_on=[EventB, EventC])
        async def join(self, ctx: Context, events: dict) -> StopEvent:
            return StopEvent(result="done")

    assert ParallelWorkflow is not None


# ============================================================================
# Part 2: Buffer Size Limit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_buffer_size_limit_exceeded():
    """Test that deadlock is detected when events are buffered but workflow cannot complete."""

    # Create a workflow that generates buffered events without completing
    class BufferTestWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            # Emit events that will be buffered
            await ctx.emit(EventA())
            await ctx.emit(EventB())
            await ctx.emit(EventC())
            # Don't emit EventD, so join4 remains pending
            return None

        @step(depends_on=[EventA, EventB])
        async def join1(self, ctx: Context, events: dict) -> None:
            # Don't return anything to keep workflow running
            return None

        @step(depends_on=[EventA, EventC])
        async def join2(self, ctx: Context, events: dict) -> None:
            return None

        @step(depends_on=[EventB, EventC])
        async def join3(self, ctx: Context, events: dict) -> None:
            return None

        # This step will never execute because EventD is never emitted
        @step(depends_on=[EventA, EventD])
        async def join4(self, ctx: Context, events: dict) -> StopEvent:
            return StopEvent(result="join4")

    workflow = BufferTestWorkflow()

    # This should trigger deadlock detection
    # join4 has EventA buffered but EventD never arrives
    with pytest.raises(WorkflowRuntimeError) as exc_info:
        await workflow.run(max_buffer_size=10)

    # Should detect deadlock
    error_msg = str(exc_info.value).lower()
    assert "deadlock" in error_msg


@pytest.mark.asyncio
async def test_buffer_size_within_limit():
    """Test that workflows within buffer limits work correctly."""

    class SmallBufferWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            await ctx.emit(EventA())
            return EventB()

        @step(depends_on=[EventA, EventB])
        async def join(self, ctx: Context, events: dict) -> StopEvent:
            return StopEvent(result="done")

    workflow = SmallBufferWorkflow()
    result = await workflow.run(max_buffer_size=100)

    assert result == "done"


# ============================================================================
# Part 3: Deadlock Detection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_deadlock_detection_missing_event():
    """Test that deadlock is detected when events are missing."""

    class DeadlockWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            # Only emit EventA, but join needs both EventA and EventB
            return EventA()

        @step(depends_on=[EventA, EventB])
        async def join(self, ctx: Context, events: dict) -> StopEvent:
            return StopEvent(result="done")

    workflow = DeadlockWorkflow()

    with pytest.raises(WorkflowRuntimeError) as exc_info:
        await workflow.run()

    assert "deadlock detected" in str(exc_info.value).lower()
    assert "missing" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_no_deadlock_all_events_present():
    """Test that no deadlock is detected when all events are present."""

    class NoDeadlockWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            await ctx.emit(EventA())
            return EventB()

        @step(depends_on=[EventA, EventB])
        async def join(self, ctx: Context, events: dict) -> StopEvent:
            return StopEvent(result="done")

    workflow = NoDeadlockWorkflow()
    result = await workflow.run()

    assert result == "done"


@pytest.mark.asyncio
async def test_deadlock_detection_join_steps():
    """Test deadlock detection with multiple pending steps."""

    class JoinDeadlockWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            return EventA()

        @step(depends_on=[EventA, EventB])
        async def join1(self, ctx: Context, events: dict) -> EventC:
            return EventC()

        @step(depends_on=[EventA, EventC])
        async def join2(self, ctx: Context, events: dict) -> StopEvent:
            return StopEvent(result="done")

    workflow = JoinDeadlockWorkflow()

    with pytest.raises(WorkflowRuntimeError) as exc_info:
        await workflow.run()

    error_msg = str(exc_info.value).lower()
    assert "deadlock detected" in error_msg
    assert "pending steps" in error_msg


# ============================================================================
# Part 4: Error Message Quality Tests
# ============================================================================


@pytest.mark.asyncio
async def test_join_step_error_includes_context():
    """Test that join step errors include helpful context."""

    class ErrorWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            await ctx.emit(EventA())
            return EventB()

        @step(depends_on=[EventA, EventB])
        async def join(self, ctx: Context, events: dict) -> StopEvent:
            # Force an error
            raise ValueError("Test error")

    workflow = ErrorWorkflow()

    with pytest.raises(WorkflowRuntimeError) as exc_info:
        await workflow.run()

    error_msg = str(exc_info.value)
    assert "join" in error_msg
    assert "EventA" in error_msg
    assert "EventB" in error_msg
    assert "Test error" in error_msg


@pytest.mark.asyncio
async def test_buffer_error_includes_step_names():
    """Test that buffer errors include step names."""

    class BufferErrorWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            return EventA()

        @step(depends_on=[EventA, EventB])
        async def join(self, ctx: Context, events: dict) -> StopEvent:
            return StopEvent(result="done")

    workflow = BufferErrorWorkflow()

    with pytest.raises(WorkflowRuntimeError) as exc_info:
        await workflow.run()

    error_msg = str(exc_info.value)
    assert "join" in error_msg


@pytest.mark.asyncio
async def test_timeout_error_includes_event_info():
    """Test that timeout errors include event information."""

    class TimeoutWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            await ctx.emit(EventA())
            return EventB()

        @step(depends_on=[EventA, EventB], timeout=0.001)
        async def join(self, ctx: Context, events: dict) -> StopEvent:
            # Sleep longer than timeout
            import asyncio

            await asyncio.sleep(1)
            return StopEvent(result="done")

    workflow = TimeoutWorkflow()

    with pytest.raises(Exception) as exc_info:
        await workflow.run()

    error_msg = str(exc_info.value)
    # Should mention the step name and required events
    assert "join" in error_msg or "timeout" in error_msg.lower()


# ============================================================================
# Part 5: Event Buffer Diagnostic Tests
# ============================================================================


@pytest.mark.asyncio
async def test_event_buffer_get_pending_steps():
    """Test that get_pending_steps returns correct step names."""
    from novastack.workflows.runtime.event_buffer import EventBuffer

    buffer = EventBuffer()

    # Initially empty
    assert buffer.get_pending_steps() == []

    # Add events for different steps
    await buffer.add_event("step1", EventA())
    await buffer.add_event("step2", EventB())

    pending = buffer.get_pending_steps()
    assert "step1" in pending
    assert "step2" in pending
    assert len(pending) == 2

    # Clear one step
    await buffer.clear_events("step1")
    pending = buffer.get_pending_steps()
    assert "step1" not in pending
    assert "step2" in pending


@pytest.mark.asyncio
async def test_event_buffer_get_step_status():
    """Test that get_step_status returns correct event types."""
    from novastack.workflows.runtime.event_buffer import EventBuffer

    buffer = EventBuffer()

    # No events yet
    assert buffer.get_step_status("step1") == {}

    # Add events
    await buffer.add_event("step1", EventA())
    await buffer.add_event("step1", EventB())

    status = buffer.get_step_status("step1")
    assert "EventA" in status
    assert "EventB" in status
    assert status["EventA"] is True
    assert status["EventB"] is True


# ============================================================================
# Part 6: Backward Compatibility Tests
# ============================================================================


@pytest.mark.asyncio
async def test_single_event_steps_unaffected():
    """Test that single-event steps work as before."""

    class SingleEventWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            return EventA()

        @step(depends_on=EventA)
        async def process(self, ctx: Context, ev: EventA) -> StopEvent:
            return StopEvent(result="single_event_works")

    workflow = SingleEventWorkflow()
    result = await workflow.run()

    assert result == "single_event_works"


@pytest.mark.asyncio
async def test_exception_inheritance():
    """Test that workflow exceptions inherit from WorkflowError."""
    from novastack.workflows.exceptions import (
        WorkflowError,
        WorkflowRuntimeError,
        WorkflowValidationError,
    )

    assert issubclass(WorkflowValidationError, WorkflowError)
    assert issubclass(WorkflowRuntimeError, WorkflowError)


# ============================================================================
# Part 7: Edge Cases and Complex Scenarios
# ============================================================================


@pytest.mark.asyncio
async def test_sequential_join_steps():
    """Test workflow with sequential chained join steps."""

    class MultiJoinWorkflow(Workflow):
        @step(depends_on=StartEvent)
        async def start(self, ctx: Context, ev: StartEvent) -> EventA:
            await ctx.emit(EventA())
            await ctx.emit(EventB())
            return EventC()

        @step(depends_on=[EventA, EventB])
        async def join1(self, ctx: Context, events: dict) -> EventD:
            return EventD()

        @step(depends_on=[EventC, EventD])
        async def join2(self, ctx: Context, events: dict) -> StopEvent:
            return StopEvent(result="multi_join_works")

    workflow = MultiJoinWorkflow()
    result = await workflow.run()

    assert result == "multi_join_works"
