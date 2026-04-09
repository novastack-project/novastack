import pytest
from pydantic import BaseModel, Field
from novastack.workflows import Workflow, Context, step, StartEvent, StopEvent


class CounterState(BaseModel):
    counter: int = Field(default=0)
    run_count: int = Field(default=0)


class CounterWorkflow(Workflow):
    """
    - State persists when the same context is reused
    - Multiple workflow executions with the same context
    - Counter incrementing across runs
    """

    @step(on=StartEvent)
    async def increment_counter(
        self, ctx: Context[CounterState], ev: StartEvent
    ) -> StopEvent:
        current_counter = ctx.state.counter
        current_run_count = ctx.state.run_count

        # Increment with copy-on-write
        async with ctx.store.edit_state() as state:
            state.counter = current_counter + 1
            state.run_count = current_run_count + 1

        # Get increment value from event or use default
        ev.get("increment_by", 1)

        return StopEvent(
            result={
                "counter": ctx.state.counter,
                "run_count": ctx.state.run_count,
            }
        )


class GenericStateWorkflow(Workflow):
    """
    - Automatic state initialization with DictLikeModel
    - DictLikeModel allows dynamic field assignment like a dictionary
    """

    @step(on=StartEvent)
    async def start(self, ctx: Context, ev: StartEvent) -> StopEvent:
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


@pytest.mark.asyncio
async def test_state_persistence():
    workflow = CounterWorkflow()

    # Create a single context that will be reused
    ctx = Context(workflow)

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


@pytest.mark.asyncio
async def test_state_persistence_new_context():
    workflow = CounterWorkflow()

    # First context
    ctx1 = Context(workflow)
    result1 = await workflow.run(ctx=ctx1)
    assert result1["counter"] == 1
    assert result1["run_count"] == 1

    # New context - should start fresh
    ctx2 = Context(workflow)
    result2 = await workflow.run(ctx=ctx2)
    assert result2["counter"] == 1  # Fresh start!
    assert result2["run_count"] == 1


@pytest.mark.asyncio
async def test_state_persistence_multiple_runs():
    workflow = CounterWorkflow()
    ctx = Context(workflow)

    # Run workflow 10 times
    for i in range(1, 11):
        result = await workflow.run(ctx=ctx)
        assert result["counter"] == i
        assert result["run_count"] == i


@pytest.mark.asyncio
async def test_generic_state_workflow():
    workflow = GenericStateWorkflow()
    result = await workflow.run(input_msg="test")

    assert result["counter"] == 1
    assert result["message"] == "Hello from generic state"
    assert result["items"] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_generic_state_workflow_multiple_runs():
    workflow = GenericStateWorkflow()
    ctx = Context(workflow)

    # First run
    result1 = await workflow.run(ctx=ctx)
    assert result1["counter"] == 1

    # Second run - state is reset because we're creating new state each time
    result2 = await workflow.run(ctx=ctx)
    assert result2["counter"] == 1  # Reset each run in this workflow


@pytest.mark.asyncio
async def test_state_isolation_between_workflows():
    workflow1 = CounterWorkflow()
    workflow2 = CounterWorkflow()

    ctx1 = Context(workflow1)
    ctx2 = Context(workflow2)

    # Run workflow1 twice
    await workflow1.run(ctx=ctx1)
    result1b = await workflow1.run(ctx=ctx1)
    assert result1b["counter"] == 2

    # Run workflow2 once - should start fresh
    result2 = await workflow2.run(ctx=ctx2)
    assert result2["counter"] == 1
