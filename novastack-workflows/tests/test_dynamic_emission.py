import pytest
from typing import Any
from pydantic import BaseModel, Field
from novastack.workflows import Workflow, Context, step, Event, StartEvent, StopEvent


class TaskEvent(Event):
    task_id: int
    data: str


class TaskCompleteEvent(Event):
    task_id: int
    result: str


class DynamicState(BaseModel):
    total_tasks: int = Field(default=0)
    completed_tasks: int = Field(default=0)
    results: list[dict[str, Any]] = Field(default_factory=list)


class DynamicWorkflow(Workflow):
    """
    - Using ctx.emit() for manual event emission
    - Multiple events emitted from a single step
    - Copy-on-write state for tracking
    - Flexible event patterns with immutable state
    """

    @step(on=StartEvent)
    async def split_tasks(self, ctx: Context, ev: StartEvent) -> None:
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
        result = ev.data.upper()
        return TaskCompleteEvent(task_id=ev.task_id, result=result)

    @step(on=TaskCompleteEvent)
    async def collect_task_results(
        self, ctx: Context, ev: TaskCompleteEvent
    ) -> StopEvent | None:
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


@pytest.mark.asyncio
async def test_dynamic_emission():
    workflow = DynamicWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx)

    assert len(result) == 3
    assert result[0]["result"] == "TASK A"
    assert result[1]["result"] == "TASK B"
    assert result[2]["result"] == "TASK C"


@pytest.mark.asyncio
async def test_dynamic_emission_task_ids():
    workflow = DynamicWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx)

    assert result[0]["task_id"] == 1
    assert result[1]["task_id"] == 2
    assert result[2]["task_id"] == 3


@pytest.mark.asyncio
async def test_dynamic_emission_all_tasks_processed():
    workflow = DynamicWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx)

    # Verify all 3 tasks were processed
    assert len(result) == 3
    
    # Verify each task was processed correctly
    for i, task_result in enumerate(result, start=1):
        assert task_result["task_id"] == i
        assert isinstance(task_result["result"], str)
        assert task_result["result"].isupper()
