import asyncio

import pytest
from novastack.workflows.events import Event, StartEvent, StopEvent
from novastack.workflows.runtime.event_buffer import EventBuffer


class EventA(Event):
    """Test event A."""

    data: str = "a"


class EventB(Event):
    """Test event B."""

    data: str = "b"


class EventC(Event):
    """Test event C."""

    data: str = "c"


@pytest.mark.asyncio
async def test_event_buffer_initialization():
    """Test that EventBuffer initializes correctly."""
    buffer = EventBuffer()
    assert buffer.get_buffer_size() == 0


@pytest.mark.asyncio
async def test_add_single_event():
    """Test adding a single event to the buffer."""
    buffer = EventBuffer()
    event = EventA(data="test")

    await buffer.add_event("step1", event)

    assert buffer.get_buffer_size() == 1


@pytest.mark.asyncio
async def test_add_multiple_events_same_step():
    """Test adding multiple different events to the same step."""
    buffer = EventBuffer()
    event_a = EventA(data="a")
    event_b = EventB(data="b")

    await buffer.add_event("step1", event_a)
    await buffer.add_event("step1", event_b)

    assert buffer.get_buffer_size() == 2


@pytest.mark.asyncio
async def test_add_events_different_steps():
    """Test adding events to different steps."""
    buffer = EventBuffer()

    await buffer.add_event("step1", EventA(data="a1"))
    await buffer.add_event("step2", EventA(data="a2"))
    await buffer.add_event("step1", EventB(data="b1"))

    assert buffer.get_buffer_size() == 3


@pytest.mark.asyncio
async def test_duplicate_event_overwrite():
    """Test that duplicate events overwrite previous ones."""
    buffer = EventBuffer()

    event_first = EventA(data="first")
    event_second = EventA(data="second")

    await buffer.add_event("step1", event_first)
    await buffer.add_event("step1", event_second)

    # Should only have one event (overwritten)
    assert buffer.get_buffer_size() == 1

    # Verify it's the latest event
    events = await buffer.get_events("step1", {EventA})
    assert events is not None
    assert events[EventA].data == "second"


@pytest.mark.asyncio
async def test_has_all_events_empty_buffer():
    """Test get_events with empty buffer."""
    buffer = EventBuffer()

    events = await buffer.get_events("step1", {EventA, EventB})
    assert events is None


@pytest.mark.asyncio
async def test_has_all_events_partial():
    """Test get_events with partial events."""
    buffer = EventBuffer()

    await buffer.add_event("step1", EventA(data="a"))

    events = await buffer.get_events("step1", {EventA, EventB})
    assert events is None


@pytest.mark.asyncio
async def test_has_all_events_complete():
    """Test get_events when all events are present."""
    buffer = EventBuffer()

    await buffer.add_event("step1", EventA(data="a"))
    await buffer.add_event("step1", EventB(data="b"))

    events = await buffer.get_events("step1", {EventA, EventB})
    assert events is not None


@pytest.mark.asyncio
async def test_has_all_events_extra_events():
    """Test get_events when buffer has more events than required."""
    buffer = EventBuffer()

    await buffer.add_event("step1", EventA(data="a"))
    await buffer.add_event("step1", EventB(data="b"))
    await buffer.add_event("step1", EventC(data="c"))

    # Should return events even with extra events in buffer
    events = await buffer.get_events("step1", {EventA, EventB})
    assert events is not None


@pytest.mark.asyncio
async def test_get_events_not_ready():
    """Test get_events returns None when not all events present."""
    buffer = EventBuffer()

    await buffer.add_event("step1", EventA(data="a"))

    events = await buffer.get_events("step1", {EventA, EventB})
    assert events is None


@pytest.mark.asyncio
async def test_get_events_ready():
    """Test get_events returns events when all are present."""
    buffer = EventBuffer()

    event_a = EventA(data="a")
    event_b = EventB(data="b")

    await buffer.add_event("step1", event_a)
    await buffer.add_event("step1", event_b)

    events = await buffer.get_events("step1", {EventA, EventB})

    assert events is not None
    assert EventA in events
    assert EventB in events
    assert events[EventA].data == "a"
    assert events[EventB].data == "b"


@pytest.mark.asyncio
async def test_get_events_only_required():
    """Test get_events returns only required events."""
    buffer = EventBuffer()

    await buffer.add_event("step1", EventA(data="a"))
    await buffer.add_event("step1", EventB(data="b"))
    await buffer.add_event("step1", EventC(data="c"))

    # Request only A and B
    events = await buffer.get_events("step1", {EventA, EventB})

    assert events is not None
    assert len(events) == 2
    assert EventA in events
    assert EventB in events
    assert EventC not in events


@pytest.mark.asyncio
async def test_get_events_nonexistent_step():
    """Test get_events with nonexistent step."""
    buffer = EventBuffer()

    events = await buffer.get_events("nonexistent", {EventA})
    assert events is None


@pytest.mark.asyncio
async def test_clear_events():
    """Test clearing events for a step."""
    buffer = EventBuffer()

    await buffer.add_event("step1", EventA(data="a"))
    await buffer.add_event("step1", EventB(data="b"))

    assert buffer.get_buffer_size() == 2

    await buffer.clear_events("step1")

    assert buffer.get_buffer_size() == 0
    events = await buffer.get_events("step1", {EventA, EventB})
    assert events is None


@pytest.mark.asyncio
async def test_clear_events_preserves_other_steps():
    """Test that clearing one step doesn't affect others."""
    buffer = EventBuffer()

    await buffer.add_event("step1", EventA(data="a1"))
    await buffer.add_event("step2", EventA(data="a2"))

    await buffer.clear_events("step1")

    assert buffer.get_buffer_size() == 1
    events = await buffer.get_events("step2", {EventA})
    assert events is not None
    assert events[EventA].data == "a2"


@pytest.mark.asyncio
async def test_clear_events_nonexistent_step():
    """Test clearing nonexistent step doesn't raise error."""
    buffer = EventBuffer()

    # Should not raise any exception
    await buffer.clear_events("nonexistent")
    assert buffer.get_buffer_size() == 0


@pytest.mark.asyncio
async def test_get_buffer_size_multiple_steps():
    """Test buffer size calculation across multiple steps."""
    buffer = EventBuffer()

    await buffer.add_event("step1", EventA(data="a1"))
    await buffer.add_event("step1", EventB(data="b1"))
    await buffer.add_event("step2", EventA(data="a2"))
    await buffer.add_event("step3", EventC(data="c3"))

    assert buffer.get_buffer_size() == 4


@pytest.mark.asyncio
async def test_concurrent_add_events():
    """Test thread-safety with concurrent event additions."""
    buffer = EventBuffer()

    async def add_events(step_name: str, count: int):
        for i in range(count):
            await buffer.add_event(step_name, EventA(data=f"{step_name}_{i}"))

    # Add events concurrently from multiple tasks
    await asyncio.gather(
        add_events("step1", 10),
        add_events("step2", 10),
        add_events("step3", 10),
    )

    # Each step should have 1 event (last one wins due to overwrite)
    assert buffer.get_buffer_size() == 3


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test thread-safety with mixed concurrent operations."""
    buffer = EventBuffer()

    async def add_and_check(step_name: str):
        await buffer.add_event(step_name, EventA(data="a"))
        await buffer.add_event(step_name, EventB(data="b"))
        events = await buffer.get_events(step_name, {EventA, EventB})
        if events is not None:
            await buffer.clear_events(step_name)
        return events is not None

    # Run multiple concurrent workflows
    results = await asyncio.gather(*[add_and_check(f"step{i}") for i in range(10)])

    # All should complete successfully
    assert all(results)
    assert buffer.get_buffer_size() == 0


@pytest.mark.asyncio
async def test_workflow_simulation():
    """Test simulating a complete workflow fan-in scenario."""
    buffer = EventBuffer()
    step_name = "join_step"

    # Simulate parallel branches producing events
    await buffer.add_event(step_name, EventA(data="branch_a"))

    # Check if ready (should be None - not all events present)
    events = await buffer.get_events(step_name, {EventA, EventB})
    assert events is None

    # Second branch completes
    await buffer.add_event(step_name, EventB(data="branch_b"))

    # Check if ready (should return events)
    events = await buffer.get_events(step_name, {EventA, EventB})
    assert events is not None

    # Retrieve events for execution
    events = await buffer.get_events(step_name, {EventA, EventB})
    assert events is not None
    assert events[EventA].data == "branch_a"
    assert events[EventB].data == "branch_b"

    # Clear after successful execution
    await buffer.clear_events(step_name)
    assert buffer.get_buffer_size() == 0


@pytest.mark.asyncio
async def test_join_step_isolation():
    """Test that different steps maintain isolated event buffers."""
    buffer = EventBuffer()

    # Add events to different steps
    await buffer.add_event("step1", EventA(data="step1_a"))
    await buffer.add_event("step1", EventB(data="step1_b"))
    await buffer.add_event("step2", EventA(data="step2_a"))
    await buffer.add_event("step2", EventB(data="step2_b"))

    # Check step1
    events1 = await buffer.get_events("step1", {EventA, EventB})
    assert events1 is not None
    assert events1[EventA].data == "step1_a"
    assert events1[EventB].data == "step1_b"

    # Check step2
    events2 = await buffer.get_events("step2", {EventA, EventB})
    assert events2 is not None
    assert events2[EventA].data == "step2_a"
    assert events2[EventB].data == "step2_b"

    # Clear step1 shouldn't affect step2
    await buffer.clear_events("step1")
    events2_after = await buffer.get_events("step2", {EventA, EventB})
    assert events2_after is not None
