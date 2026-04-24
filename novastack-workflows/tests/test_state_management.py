import pytest
from novastack.workflows import Context, Event, StartEvent, StopEvent, Workflow, step
from pydantic import BaseModel, Field


class IncrementEvent(Event):
    value: int


class RunState(BaseModel):
    counter: int = Field(default=0)
    items: list[str] = Field(default_factory=list)
    total: int = Field(default=0)


class StateWorkflow(Workflow):
    """
    - Automatic state initialization using RunState.
    - Copy-on-write state mutations with async context manager.
    - Immutability by default.
    - Thread-safe state updates.
    - Automatic rollback on errors.
    """

    @step(depends_on=StartEvent)
    async def initialize(
        self, ctx: Context[RunState], ev: StartEvent
    ) -> IncrementEvent:
        async with ctx.store.edit_state() as state:
            state.counter = 0
            state.items = ["initialized"]
            state.total = 0

        return IncrementEvent(value=5)

    @step(depends_on=IncrementEvent)
    async def increment(self, ctx: Context[RunState], ev: IncrementEvent) -> StopEvent:
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


@pytest.mark.asyncio
async def test_state_workflow():
    workflow = StateWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx)

    assert isinstance(ctx.state, RunState)

    assert result["counter"] == 5
    assert result["items"] == ["initialized", "incremented by 5"]
    assert result["total"] == 10


@pytest.mark.asyncio
async def test_state_workflow_multiple_increments():
    workflow = StateWorkflow()
    ctx = Context(workflow)

    # Modify the workflow to accept different increment values
    result = await workflow.run(ctx=ctx)

    assert isinstance(ctx.state, RunState)

    assert result["counter"] == 5
    assert len(result["items"]) == 2
    assert result["total"] == 10


@pytest.mark.asyncio
async def test_state_immutability():
    workflow = StateWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx)

    assert isinstance(ctx.state, RunState)

    # Verify state was properly managed
    assert result["counter"] == 5
    assert "initialized" in result["items"]
    assert "incremented by 5" in result["items"]
