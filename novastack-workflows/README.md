# NovaStack Workflows

A powerful and flexible event-driven workflow engine for Python, designed to build complex asynchronous workflows with ease.

## Installation

```bash
pip install novastack-workflows
```

## Quick Start

Here's a simple example to get you started with NovaStack Workflows:

```python
from novastack.workflows import Workflow, Context, step
from novastack.workflows.events import Event, StartEvent, StopEvent


class MyEvent(Event):
    message: str

class SimpleWorkflow(Workflow):

    @step(depends_on=StartEvent)
    async def start(self, ctx: Context, ev: StartEvent) -> MyEvent:
        
        input_msg = ev.get("input_msg", "")
        
        return MyEvent(message=f"Processed: {input_msg}")

    @step(depends_on=MyEvent)
    async def process(self, ctx: Context, ev: MyEvent) -> StopEvent:
        
        return StopEvent(result=ev.message)


async def main():
    workflow = SimpleWorkflow()
    result = await workflow.run(input_msg="Hello, World!")

    print(result)
```

## Core Concepts

### Workflow

A workflow is a class that inherits from `Workflow` and contains one or more steps. It orchestrates the execution of steps based on events.

### Steps

Steps are methods decorated with `@step(depends_on=EventType)` that define what happens when a specific event is received.

- Steps are asynchronous functions that receive a `Context` and an `Event`
- Steps can return new events to trigger subsequent steps

### Events

Events are the building blocks of workflows. They carry data between steps and trigger step execution.

- **StartEvent**: Automatically triggered when a workflow starts
- **StopEvent**: Signals the end of a workflow and carries the final result
- **Custom Events**: Define your own events by inheriting from `Event`

### Context

The `Context` object provides access to workflow state and allows steps to share data throughout the workflow execution.
