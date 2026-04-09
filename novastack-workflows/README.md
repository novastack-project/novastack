# NovaStack Workflows

A powerful and flexible event-driven workflow engine for Python, designed to build complex asynchronous workflows with ease.

## Installation

```bash
pip install novastack-workflows
```

## Quick Start

Here's a simple example to get you started with NovaStack Workflows:

```python
from novastack.workflows import Workflow, Context, step, Event, StartEvent, StopEvent


# Define a custom event
class MyEvent(Event):
    message: str

# Create your workflow
class SimpleWorkflow(Workflow):
    """A simple workflow that processes a message."""

    @step(on=StartEvent)
    async def start(self, ctx: Context, ev: StartEvent) -> MyEvent:
        # Get input from the start event
        input_msg = ev.get("input_msg", "")
        # Return a custom event to trigger the next step
        return MyEvent(message=f"Processed: {input_msg}")

    @step(on=MyEvent)
    async def process(self, ctx: Context, ev: MyEvent) -> StopEvent:
        # Process the message and return the final result
        return StopEvent(result=ev.message)


# Run the workflow
async def main():
    workflow = SimpleWorkflow()
    result = await workflow.run(input_msg="Hello, World!")
    print(result)  # Output: Processed: Hello, World!
```

## Core Concepts

### Events

Events are the building blocks of workflows. They carry data between steps and trigger step execution.

- **StartEvent**: Automatically triggered when a workflow starts
- **StopEvent**: Signals the end of a workflow and carries the final result
- **Custom Events**: Define your own events by inheriting from `Event`

### Steps

Steps are methods decorated with `@step(on=EventType)` that define what happens when a specific event is received.

- Steps are asynchronous functions that receive a `Context` and an `Event`
- Steps can return new events to trigger subsequent steps

### Workflow

A workflow is a class that inherits from `Workflow` and contains one or more steps. It orchestrates the execution of steps based on events.

### Context

The `Context` object provides access to workflow state and allows steps to share data throughout the workflow execution.
