import asyncio
import random

import pytest
from novastack.workflows import Context, Event, StartEvent, StopEvent, Workflow, step
from pydantic import BaseModel, Field


class ApiCallEvent(Event):
    endpoint: str


class ApiResponseEvent(Event):
    data: str
    attempts: int


class ApiProcessedEvent(Event):
    result: str


class ApiState(BaseModel):
    start_time: float = Field(default=0.0)
    api_attempts: int = Field(default=0)


class ResilientApiWorkflow(Workflow):
    """
    - Step timeout (5 seconds max).
    - Automatic retry (up to 3 attempts).
    - 1 second delay between retries.
    - Error handling for timeout and retry exhaustion.
    - Thread-safe state tracking with copy-on-write.
    """

    @step(depends_on=StartEvent)
    async def start(self, ctx: Context[ApiState], ev: StartEvent) -> ApiCallEvent:
        async with ctx.store.edit_state() as state:
            state.start_time = asyncio.get_event_loop().time()

        return ApiCallEvent(endpoint=ev.get("input_msg", "/api/default"))

    @step(
        depends_on=ApiCallEvent,
        timeout=5.0,  # 5 second timeout
        max_retries=3,  # Retry up to 3 times
        retry_delay=1.0,  # 1 second delay between retries
    )
    async def call_flaky_api(
        self, ctx: Context[ApiState], ev: ApiCallEvent
    ) -> ApiResponseEvent:
        attempt = ctx.state.api_attempts + 1

        # Update attempts with copy-on-write
        async with ctx.store.edit_state() as state:
            state.api_attempts = attempt

        # Simulate random failures (50% chance)
        if random.random() < 0.5 and attempt < 3:
            raise Exception(f"API temporarily unavailable (attempt {attempt})")

        # Simulate API delay
        await asyncio.sleep(0.2)

        return ApiResponseEvent(data=f"Response from {ev.endpoint}", attempts=attempt)

    @step(depends_on=ApiResponseEvent, timeout=2.0)
    async def process_response(
        self, ctx: Context[ApiState], ev: ApiResponseEvent
    ) -> ApiProcessedEvent:
        await asyncio.sleep(0.1)

        processed = ev.data.upper()
        return ApiProcessedEvent(result=processed)

    @step(depends_on=ApiProcessedEvent)
    async def finish(self, ctx: Context[ApiState], ev: ApiProcessedEvent) -> StopEvent:
        elapsed = asyncio.get_event_loop().time() - ctx.state.start_time
        total_attempts = ctx.state.api_attempts

        result = {
            "result": ev.result,
            "total_attempts": total_attempts,
            "elapsed_time": f"{elapsed:.2f}s",
        }

        return StopEvent(result=result)


@pytest.mark.asyncio
async def test_timeout_retry_workflow():
    workflow = ResilientApiWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx, input_msg="/api/data")

    assert result["total_attempts"] >= 1
    assert "RESPONSE FROM /API/DATA" in result["result"]


@pytest.mark.asyncio
async def test_timeout_retry_workflow_different_endpoint():
    workflow = ResilientApiWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx, input_msg="/api/users")

    assert result["total_attempts"] >= 1
    assert "RESPONSE FROM /API/USERS" in result["result"]


@pytest.mark.asyncio
async def test_timeout_retry_workflow_tracks_attempts():
    workflow = ResilientApiWorkflow()
    ctx = Context(workflow)
    result = await workflow.run(ctx=ctx, input_msg="/api/test")

    # Should have at least 1 attempt, at most 3 (with retries)
    assert 1 <= result["total_attempts"] <= 4
    assert isinstance(result["elapsed_time"], str)
    assert "s" in result["elapsed_time"]
