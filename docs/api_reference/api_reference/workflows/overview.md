---
title: Overview
---

A powerful and flexible event-driven workflow engine for Python, designed to build complex asynchronous workflows with ease.

## Installation

```bash
pip install novastack-workflows
```

## Quick Start

Here's a simple example to get you started with Novastack Workflows:

```python
from novastack_workflows import Workflow, Context, step
from novastack_workflows.events import Event, StartEvent, StopEvent


class MessageEvent(Event):
    message: str

class MyWorkflow(Workflow):

    @step(when=StartEvent)
    async def start(self, ctx: Context, ev: StartEvent) -> MessageEvent:
        
        input_msg = ev.get("message", "")
        return MessageEvent(message=f"Processed: {input_msg}")

    @step(when=MessageEvent)
    async def process(self, ctx: Context, ev: MessageEvent) -> StopEvent:
        return StopEvent(result=ev.message)


async def main():
    workflow = MyWorkflow()
    result = await workflow.run(input_msg="Hello, World!")

    print(result)
```

## Core Concepts

### Workflow

A workflow is a class that inherits from `Workflow` and contains one or more steps. It orchestrates the execution of steps based on events.

### Steps

Steps are asynchronous methods decorated with `@step(when=EventType)` that define what happens when a specific event is received.

- Steps receive a `Context` and an `Event`.
- Steps can return new events to trigger subsequent steps.

### Events

Events are the building blocks of workflows. They carry data between steps and trigger step execution.

- **StartEvent**: Automatically triggered when a workflow starts
- **StopEvent**: Signals the end of a workflow and carries the final result
- **Custom Events**: Define your own events by inheriting from `Event`

### Context

The `Context` object provides access to workflow state and allows steps to share data throughout the workflow execution.

```python
# Read-only access
current_value = ctx.state.count

# Edit state
async with ctx.store.edit_state() as state:
    state.count = current_counter + 1

# Emit events
ctx.send_event(MyEvent(...))
```
## Features

| Feature                | Novastack Workflows     |
| ---------------------- | ----------------------- |
| Event-driven execution | ✅                       |
| Fan-out (parallelism)  | ✅                       |
| Async execution        | ✅                       |
| Shared state           | ✅                       |
| Event joins            | ✅                       |
| Internal buffer.       | ✅                       |
| Declarative API        | ✅                       |

## License

Apache License 2.0
