---
title: Run as a Server
---

Provides a production-ready HTTP API server for managing and executing workflows. This FastAPI-based server exposes RESTful endpoints for workflow registration discovery. The server maintains an internal registry of workflowsand handles concurrent execution.

## Installation

```bash
pip install "novastack-workflows[server]"
```

## Usage Example:

```python
from novastack_workflows.server import WorkflowServer
from novastack.workflows import Workflow, Context, step
from novastack.workflows.events import Event, StartEvent, StopEvent

class MessageEvent(Event):
    message: str

class MyWorkflow(Workflow):

    @step(depends_on=StartEvent)
    async def start(self, ctx: Context, ev: StartEvent) -> MessageEvent:

        input_msg = ev.get("input_msg", "")
        return MessageEvent(message=f"Processed: {input_msg}")

    @step(depends_on=MessageEvent)
    async def process(self, ctx: Context, ev: MessageEvent) -> StopEvent:
        return StopEvent(result=ev.message)


workflow = MyWorkflow()

server = WorkflowServer()
server.add_workflow("my_workflow", workflow)

import asyncio

async def main():
    await server.serve(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference


| Method | Path                            | Description                                                                                                                                                     |
| ------ | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/workflows`                    | Lists all registered workflows.                                                                                                                    |
| `POST` | `/workflows/{workflow_id}/run`         | Runs the workflow and returns the final result.                                                                                         |                                                                                    |
