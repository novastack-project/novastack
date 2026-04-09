import pytest
from novastack.workflows import Workflow, Context, step, Event, StartEvent, StopEvent


class MyEvent(Event):
    message: str


class SimpleWorkflow(Workflow):
    """
    - Workflow without state management
    - Simple event chaining: StartEvent → MyEvent → StopEvent
    - Basic decorator usage with @step(on=...)
    - Returning events from step methods
    """

    @step(on=StartEvent)
    async def start(self, ctx: Context, ev: StartEvent) -> MyEvent:
        input_msg = ev.get("input_msg", "")
        return MyEvent(message=f"Processed: {input_msg}")

    @step(on=MyEvent)
    async def process(self, ctx: Context, ev: MyEvent) -> StopEvent:
        return StopEvent(result=ev.message)


@pytest.mark.asyncio
async def test_simple_workflow():
    """Test simple workflow execution with basic event chaining."""
    workflow = SimpleWorkflow()
    result = await workflow.run(input_msg="Hello, World!")

    assert result == "Processed: Hello, World!"
