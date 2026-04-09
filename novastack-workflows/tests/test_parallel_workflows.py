import pytest
from typing import Any
from pydantic import BaseModel, Field
from novastack.workflows import Workflow, Context, step, Event, StartEvent, StopEvent


class DataFetchedEvent(Event):
    data_id: int


class ProcessedEvent(Event):
    processor: str
    result: Any


class ParallelState(BaseModel):
    result: list[dict[str, Any]] = Field(default_factory=list)
    completed_count: int = Field(default=0)


class ParallelWorkflow(Workflow):
    """
    - Multiple steps listening to the same event
    - Parallel execution (fan-out pattern)
    - Thread-safe state coordination with copy-on-write
    - Natural parallelism with immutable state
    """

    @step(on=StartEvent)
    async def fetch_data(self, ctx: Context, ev: StartEvent) -> DataFetchedEvent:
        if ctx.state is None:
            ctx._store._state = ParallelState()

        # Initialize state with copy-on-write
        async with ctx.store.edit_state() as state:
            state.result = []
            state.completed_count = 0

        data_id = ev.get("data_id", 1)
        return DataFetchedEvent(data_id=data_id)

    @step(on=DataFetchedEvent)
    async def process_a(self, ctx: Context, ev: DataFetchedEvent) -> ProcessedEvent:
        result = f"Processed by A: {ev.data_id * 2}"
        return ProcessedEvent(processor="A", result=result)

    @step(on=DataFetchedEvent)
    async def process_b(self, ctx: Context, ev: DataFetchedEvent) -> ProcessedEvent:
        result = f"Processed by B: {ev.data_id * 3}"
        return ProcessedEvent(processor="B", result=result)

    @step(on=ProcessedEvent)
    async def collect_results(
        self, ctx: Context, ev: ProcessedEvent
    ) -> StopEvent | None:
        async with ctx.store.edit_state() as state:
            state.result.append(
                {
                    "processor": ev.processor,
                    "result": ev.result,
                }
            )
            state.completed_count += 1

        # Check if both parallel steps completed (read-only access)
        if ctx.state.completed_count >= 2:
            return StopEvent(result=ctx.state.result)

        return None


@pytest.mark.asyncio
async def test_parallel_workflow():
    workflow = ParallelWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx, data_id=10)

    assert len(result) == 2
    assert any(r["processor"] == "A" for r in result)
    assert any(r["processor"] == "B" for r in result)

    # Verify results contain expected values
    processor_a_result = next(r for r in result if r["processor"] == "A")
    processor_b_result = next(r for r in result if r["processor"] == "B")

    assert processor_a_result["result"] == "Processed by A: 20"
    assert processor_b_result["result"] == "Processed by B: 30"


@pytest.mark.asyncio
async def test_parallel_workflow_different_data():
    workflow = ParallelWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx, data_id=5)

    assert len(result) == 2

    processor_a_result = next(r for r in result if r["processor"] == "A")
    processor_b_result = next(r for r in result if r["processor"] == "B")

    assert processor_a_result["result"] == "Processed by A: 10"
    assert processor_b_result["result"] == "Processed by B: 15"


@pytest.mark.asyncio
async def test_parallel_workflow_zero_data():
    workflow = ParallelWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx, data_id=0)

    assert len(result) == 2

    processor_a_result = next(r for r in result if r["processor"] == "A")
    processor_b_result = next(r for r in result if r["processor"] == "B")

    assert processor_a_result["result"] == "Processed by A: 0"
    assert processor_b_result["result"] == "Processed by B: 0"
