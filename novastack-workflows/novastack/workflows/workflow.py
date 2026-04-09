import inspect
import warnings
from typing import Any, Type, get_args, get_origin

from novastack.workflows.context import Context
from novastack.workflows.exceptions import WorkflowValidationError
from novastack.workflows.decorators import is_step_method, get_step_event_type
from novastack.workflows.runtime.engine import WorkflowEngine
from novastack.workflows.events import Event, StartEvent
from novastack.workflows.types import DictLikeModel


class Workflow:
    """
    Event-driven workflow orchestration.

    Workflows are defined by decorating methods with @step(on=EventClass).
    Steps are automatically discovered and registered when the class is defined.

    State type consistency is enforced: all steps must use the same Context[StateType].

    Example:
        ```python
        class MyWorkflow(Workflow):
            @step(on=StartEvent)
            async def start(self, ctx: Context[MyState], ev: StartEvent) -> MyEvent:
                return MyEvent(data="processed")

            @step(on=MyEvent)
            async def process(self, ctx: Context[MyState], ev: MyEvent) -> StopEvent:
                return StopEvent(result="done")

        workflow = MyWorkflow()
        result = await workflow.run(input_msg="hello")
        ```
    """

    def __init_subclass__(cls, **kwargs):
        """
        Automatically discover and register @step decorated methods.

        This is called when a subclass is defined, allowing automatic
        step discovery and state type validation.
        """
        super().__init_subclass__(**kwargs)

        # Build routing table: Event class -> list of step methods
        cls._step_registry: dict[Type[Event], list[tuple[str, Any]]] = {}

        # Track state types across steps for consistency validation
        state_types: dict[str, Type] = {}

        # Discover all @step decorated methods
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if is_step_method(method):
                event_type = get_step_event_type(method)
                if event_type:
                    if event_type not in cls._step_registry:
                        cls._step_registry[event_type] = []
                    cls._step_registry[event_type].append((name, method))

                    # Extract and validate Context state type
                    sig = inspect.signature(method)
                    for param_name, param in sig.parameters.items():
                        if param.annotation != inspect.Parameter.empty:
                            origin = get_origin(param.annotation)
                            if origin is Context:
                                args = get_args(param.annotation)
                                if args:
                                    # Context[StateType] - extract StateType
                                    state_type = args[0]
                                else:
                                    # Context without type - defaults to DictLikeModel
                                    state_type = DictLikeModel

                                state_types[name] = state_type
                                break

        # Validate state type consistency across all steps
        if state_types:
            unique_types = set(state_types.values())
            if len(unique_types) > 1:
                type_details = "\n".join(
                    f"  - {step_name}: Context[{state_type.__name__}]"
                    for step_name, state_type in state_types.items()
                )
                raise WorkflowValidationError(
                    f"Inconsistent state types in workflow '{cls.__name__}'.\n"
                    f"All steps must use the same Context[StateType].\n"
                    f"Found:\n{type_details}"
                )

            # Store the validated state type for the workflow
            cls._state_type = next(iter(unique_types))
        else:
            # No typed Context found, default to DictLikeModel
            cls._state_type = DictLikeModel

    def get_steps_for_event(self, event: Event) -> list[tuple[str, Any]]:
        """Get all step methods that handle the given event type."""
        event_class = type(event)
        return self._step_registry.get(event_class, [])

    async def run(
        self,
        ctx: Context | None = None,
        start_event: StartEvent | None = None,
        max_iterations: int = 1000,
        **kwargs,
    ) -> Any:
        """
        Run the workflow and return results.

        Args:
            ctx: Optional context to use. If None, creates new context.
            start_event: Optional explicit start event. If None, creates StartEvent(**kwargs).
            max_iterations: Maximum number of iterations before stopping. Use 0 for unlimited iterations.
            **kwargs: Additional arguments. If start_event is None, used to create StartEvent.
                     If start_event is provided, kwargs are added as attributes to the event.

        Examples:
            # Using default StartEvent with kwargs
            result = await workflow.run(input_msg="hello", user_id=123)

            # Using custom start event
            custom_event = StartEvent(data="important")
            result = await workflow.run(start_event=custom_event)
        """
        # Create or merge start_event
        if start_event is None:
            start_event = StartEvent(**kwargs)
        elif kwargs:
            # Warn about merging kwargs into start_event
            warnings.warn(
                "Merging **kwargs into StartEvent. "
                "These will overwrite any existing attributes with the same name/key.",
                UserWarning,
                stacklevel=2,
            )

            # Merge kwargs into start_event
            for key, value in kwargs.items():
                setattr(start_event, key, value)

        # Create engine and execute
        runtime_engine = WorkflowEngine(workflow=self, max_iterations=max_iterations)

        # Run workflow
        workflow_result = await runtime_engine.run(start_events=start_event, ctx=ctx)

        return workflow_result.result
