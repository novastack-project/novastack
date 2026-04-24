import inspect
import warnings
from typing import Any, Type, get_args, get_origin

from novastack.workflows.context import Context
from novastack.workflows.decorators import (
    get_step_event_types,
    is_join_step,
    is_step_method,
)
from novastack.workflows.events import Event, StartEvent, StopEvent
from novastack.workflows.exceptions import (
    WorkflowValidationError,
)
from novastack.workflows.runtime.engine import WorkflowEngine
from novastack.workflows.types import DictLikeModel


class Workflow:
    """
    Event-driven workflow orchestration.

    Workflows are defined by decorating methods with @step(depends_on=EventClass).
    Steps are automatically discovered and registered when the class is defined.

    State type consistency is enforced: all steps must use the same Context[StateType].

    Example:
        ```python
        class MyWorkflow(Workflow):
            @step(depends_on=StartEvent)
            async def start(self, ctx: Context[MyState], ev: StartEvent) -> MyEvent:
                return MyEvent(data="processed")

            @step(depends_on=MyEvent)
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

        # Track join steps: step_name -> set of required event types
        cls._join_step_registry: dict[str, set[Type[Event]]] = {}

        # Track state types across steps for consistency validation
        state_types: dict[str, Type] = {}

        # Discover all @step decorated methods
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if is_step_method(method):
                event_types = get_step_event_types(method)
                if event_types:
                    if is_join_step(method):
                        cls._join_step_registry[name] = set(event_types)

                    # Add to step_registry for each event type
                    for single_event_type in event_types:
                        if single_event_type not in cls._step_registry:
                            cls._step_registry[single_event_type] = []
                        cls._step_registry[single_event_type].append((name, method))

                    # Extract and validate Context state type
                    # Parameter name is enforced to be 'ctx' by decorator validation
                    sig = inspect.signature(method)
                    ctx_param = sig.parameters.get("ctx")
                    if ctx_param and ctx_param.annotation != inspect.Parameter.empty:
                        origin = get_origin(ctx_param.annotation)
                        if origin is Context:
                            args = get_args(ctx_param.annotation)
                            if args:
                                # Context[StateType] - extract StateType
                                state_type = args[0]
                            else:
                                # Context without type - defaults to DictLikeModel
                                state_type = DictLikeModel

                            state_types[name] = state_type

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
            cls._state_type = DictLikeModel

        cls._validate_single_start_step()
        cls._warn_multiple_stop_event()

        # Detect circular dependencies in join steps
        cls._detect_circular_dependencies()

    @classmethod
    def _extract_produced_events(cls, method) -> set[Type[Event]]:
        """Extract event types produced by a step method from its return annotation."""
        produced_events: set[Type[Event]] = set()
        sig = inspect.signature(method)
        return_annotation = sig.return_annotation

        if return_annotation != inspect.Parameter.empty:
            origin = get_origin(return_annotation)
            if origin is not None:
                # Handle Union types (Event | None)
                args = get_args(return_annotation)
                for arg in args:
                    if isinstance(arg, type) and issubclass(arg, Event):
                        produced_events.add(arg)
            elif isinstance(return_annotation, type) and issubclass(
                return_annotation, Event
            ):
                # Direct Event type
                produced_events.add(return_annotation)

        return produced_events

    @classmethod
    def _build_event_producers_map(cls) -> dict[Type[Event], list[str]]:
        """Build a map of event types to the step names that produce them."""
        event_producers: dict[Type[Event], list[str]] = {}

        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if is_step_method(method):
                produced_events = cls._extract_produced_events(method)
                for event_type in produced_events:
                    if event_type not in event_producers:
                        event_producers[event_type] = []
                    event_producers[event_type].append(name)

        return event_producers

    @classmethod
    def _detect_circular_dependencies(cls) -> None:
        """
        Detect circular dependencies in join steps.

        This method builds a dependency graph and checks for cycles where
        a join step depends on events that can only be produced by
        steps that depend on this step's output.

        Raises:
            WorkflowValidationError: If circular dependencies are detected
        """
        if not cls._join_step_registry:
            return

        # Build event producers map
        event_producers = cls._build_event_producers_map()

        # Check each join step for circular dependencies
        for step_name, required_events in cls._join_step_registry.items():
            step_method = getattr(cls, step_name)
            produced_events = cls._extract_produced_events(step_method)

            # Check if any required event creates a circular dependency
            for required_event in required_events:
                if required_event not in event_producers:
                    continue

                producers = event_producers[required_event]

                # Check if any producer is a join step that requires this step's output
                for producer_name in producers:
                    if producer_name in cls._join_step_registry:
                        producer_required = cls._join_step_registry[producer_name]

                        if produced_events & producer_required:
                            raise WorkflowValidationError(
                                f"Circular dependency detected: Step '{step_name}' requires "
                                f"{required_event.__name__} which is produced by '{producer_name}', "
                                f"but '{producer_name}' requires events from '{step_name}'. "
                                f"This creates a deadlock where neither step can execute."
                            )

    @classmethod
    def _validate_single_start_step(cls) -> None:
        """
        Validate that workflow has exactly one StartEvent handler.

        Raises:
            WorkflowValidationError: If workflow has multiple StartEvent handlers
        """
        start_event_handlers = cls._step_registry.get(StartEvent, [])

        if len(start_event_handlers) > 1:
            handler_names = [name for name, _ in start_event_handlers]
            raise WorkflowValidationError(
                f"Workflow '{cls.__name__}' must have exactly one StartEvent handler. "
                f"Found {len(start_event_handlers)}: {', '.join(handler_names)}"
            )

    @classmethod
    def _warn_multiple_stop_event(cls) -> None:
        """
        Warn if multiple steps can produce StopEvent.

        Multiple StopEvent producers can cause race conditions where the first
        step to complete determines the workflow result, leading to non-deterministic behavior.
        """
        event_producers = cls._build_event_producers_map()
        stop_event_producers = event_producers.get(StopEvent, [])

        if len(stop_event_producers) > 1:
            warnings.warn(
                f"Workflow '{cls.__name__}' has {len(stop_event_producers)} steps that produce StopEvent: "
                f"{', '.join(stop_event_producers)}. This may cause race conditions.",
                UserWarning,
                stacklevel=2,
            )

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
        runtime_engine = WorkflowEngine(
            workflow=self,
            max_iterations=max_iterations,
        )

        # Run workflow
        workflow_result = await runtime_engine.run(start_events=start_event, ctx=ctx)

        return workflow_result.result
