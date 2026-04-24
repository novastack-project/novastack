import pytest
from novastack.workflows.context import Context
from novastack.workflows.decorators import (
    get_step_event_types,
    get_step_max_retries,
    get_step_name,
    get_step_retry_delay,
    get_step_timeout,
    is_join_step,
    is_step_method,
    step,
)
from novastack.workflows.events import Event, StartEvent, StopEvent
from novastack.workflows.exceptions import WorkflowValidationError


class EventA(Event):
    """Test event A."""

    data: str = "a"


class EventB(Event):
    """Test event B."""

    data: str = "b"


class EventC(Event):
    """Test event C."""

    data: str = "c"


class TestSingleEventDecorator:
    """Tests for single-event step decorator (existing behavior)."""

    def test_single_event_step_valid(self):
        """Test valid single-event step definition."""

        @step(depends_on=EventA)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert is_step_method(process)
        assert get_step_event_types(process) == [EventA]
        assert not is_join_step(process)
        assert get_step_name(process) == "process"

    def test_single_event_with_timeout(self):
        """Test single-event step with timeout."""

        @step(depends_on=EventA, timeout=30.0)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_timeout(process) == 30.0

    def test_single_event_with_retries(self):
        """Test single-event step with retry configuration."""

        @step(depends_on=EventA, max_retries=3, retry_delay=2.0)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_max_retries(process) == 3
        assert get_step_retry_delay(process) == 2.0

    def test_single_event_wrong_param_name(self):
        """Test that single-event step must use 'ev' parameter name."""
        with pytest.raises(
            WorkflowValidationError, match="must use parameter name 'ev'"
        ):

            @step(depends_on=EventA)
            async def process(self, ctx: Context, event: EventA) -> EventB:
                return EventB()

    def test_single_event_not_async(self):
        """Test that step must be async function."""
        with pytest.raises(WorkflowValidationError, match="must be an async function"):

            @step(depends_on=EventA)
            def process(self, ctx: Context, ev: EventA) -> EventB:
                return EventB()

    def test_single_event_insufficient_params(self):
        """Test that step must have at least 3 parameters."""
        with pytest.raises(WorkflowValidationError, match="at least 3 parameters"):

            @step(depends_on=EventA)
            async def process(self, ctx: Context) -> EventB:
                return EventB()


class TestJoinEventDecorator:
    """Tests for join step decorator."""

    def test_join_step_valid(self):
        """Test valid join step definition."""

        @step(depends_on=[EventA, EventB])
        async def join(self, ctx: Context, events: dict[type, Event]) -> EventC:
            return EventC()

        assert is_step_method(join)
        event_types = get_step_event_types(join)
        assert isinstance(event_types, list)
        assert set(event_types) == {EventA, EventB}
        assert is_join_step(join)
        assert get_step_name(join) == "join"

    def test_join_step_with_timeout(self):
        """Test join step with timeout."""

        @step(depends_on=[EventA, EventB], timeout=60.0)
        async def join(self, ctx: Context, events: dict[type, Event]) -> EventC:
            return EventC()

        assert get_step_timeout(join) == 60.0
        assert is_join_step(join)

    def test_join_step_with_retries(self):
        """Test join step with retry configuration."""

        @step(depends_on=[EventA, EventB], max_retries=5, retry_delay=3.0)
        async def join(self, ctx: Context, events: dict[type, Event]) -> EventC:
            return EventC()

        assert get_step_max_retries(join) == 5
        assert get_step_retry_delay(join) == 3.0

    def test_join_step_three_events(self):
        """Test join step with three event types."""

        @step(depends_on=[EventA, EventB, EventC])
        async def join_three(
            self, ctx: Context, events: dict[type, Event]
        ) -> StopEvent:
            return StopEvent()

        event_types = get_step_event_types(join_three)
        assert event_types is not None
        assert len(event_types) == 3
        assert set(event_types) == {EventA, EventB, EventC}

    def test_join_step_wrong_param_name(self):
        """Test that join step must use 'events' parameter name."""
        with pytest.raises(
            WorkflowValidationError, match="must use parameter name 'events'"
        ):

            @step(depends_on=[EventA, EventB])
            async def join(self, ctx: Context, ev: dict[type, Event]) -> EventC:
                return EventC()

    def test_join_step_wrong_param_type(self):
        """Test that join step must annotate events as dict."""
        with pytest.raises(
            WorkflowValidationError, match="must annotate 'events' parameter as 'dict"
        ):

            @step(depends_on=[EventA, EventB])
            async def join(self, ctx: Context, events: list) -> EventC:
                return EventC()

    def test_join_step_duplicate_types(self):
        """Test that duplicate event types are not allowed."""
        with pytest.raises(
            WorkflowValidationError, match="Duplicate event types not allowed"
        ):

            @step(depends_on=[EventA, EventB, EventA])
            async def join(self, ctx: Context, events: dict[type, Event]) -> EventC:
                return EventC()

    def test_join_step_non_event_type(self):
        """Test that all items must be Event subclasses."""
        with pytest.raises(WorkflowValidationError, match="must be Event subclasses"):

            @step(depends_on=[EventA, str])  # type: ignore
            async def join(self, ctx: Context, events: dict[type, Event]) -> EventC:
                return EventC()

    def test_join_step_not_async(self):
        """Test that join step must be async function."""
        with pytest.raises(WorkflowValidationError, match="must be an async function"):

            @step(depends_on=[EventA, EventB])
            def join(self, ctx: Context, events: dict[type, Event]) -> EventC:
                return EventC()

    def test_join_step_insufficient_params(self):
        """Test that join step must have at least 3 parameters."""
        with pytest.raises(WorkflowValidationError, match="at least 3 parameters"):

            @step(depends_on=[EventA, EventB])
            async def join(self, ctx: Context) -> EventC:
                return EventC()


class TestHelperFunctions:
    """Tests for decorator helper functions."""

    def test_is_step_method_true(self):
        """Test is_step_method returns True for decorated methods."""

        @step(depends_on=EventA)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert is_step_method(process) is True

    def test_is_step_method_false(self):
        """Test is_step_method returns False for non-decorated methods."""

        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert is_step_method(process) is False

    def test_get_step_event_types_single(self):
        """Test get_step_event_types normalizes single event to list."""

        @step(depends_on=EventA)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_event_types(process) == [EventA]

    def test_get_step_event_types_join(self):
        """Test get_step_event_types returns list for join."""

        @step(depends_on=[EventA, EventB])
        async def join(self, ctx: Context, events: dict[type, Event]) -> EventC:
            return EventC()

        event_types = get_step_event_types(join)
        assert isinstance(event_types, list)
        assert set(event_types) == {EventA, EventB}

    def test_get_step_event_types_none(self):
        """Test get_step_event_types returns None for non-step."""

        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_event_types(process) is None

    def test_is_join_step_single(self):
        """Test is_join_step returns False for single-event."""

        @step(depends_on=EventA)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert is_join_step(process) is False

    def test_is_join_step(self):
        """Test is_join_step returns True for join."""

        @step(depends_on=[EventA, EventB])
        async def join(self, ctx: Context, events: dict[type, Event]) -> EventC:
            return EventC()

        assert is_join_step(join) is True

    def test_is_join_step_non_step(self):
        """Test is_join_step returns False for non-step."""

        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert is_join_step(process) is False

    def test_get_step_name_valid(self):
        """Test get_step_name returns method name."""

        @step(depends_on=EventA)
        async def my_step(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_name(my_step) == "my_step"

    def test_get_step_name_none(self):
        """Test get_step_name returns None for non-step."""

        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_name(process) is None

    def test_get_step_timeout_default(self):
        """Test get_step_timeout returns None by default."""

        @step(depends_on=EventA)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_timeout(process) is None

    def test_get_step_timeout_custom(self):
        """Test get_step_timeout returns custom value."""

        @step(depends_on=EventA, timeout=45.0)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_timeout(process) == 45.0

    def test_get_step_max_retries_default(self):
        """Test get_step_max_retries returns 0 by default."""

        @step(depends_on=EventA)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_max_retries(process) == 0

    def test_get_step_max_retries_custom(self):
        """Test get_step_max_retries returns custom value."""

        @step(depends_on=EventA, max_retries=10)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_max_retries(process) == 10

    def test_get_step_retry_delay_default(self):
        """Test get_step_retry_delay returns 1.0 by default."""

        @step(depends_on=EventA)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_retry_delay(process) == 1.0

    def test_get_step_retry_delay_custom(self):
        """Test get_step_retry_delay returns custom value."""

        @step(depends_on=EventA, retry_delay=5.0)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert get_step_retry_delay(process) == 5.0


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing code."""

    def test_metadata_structure(self):
        """Test that metadata structure exists and is complete."""

        @step(depends_on=[EventA, EventB])
        async def join(self, ctx: Context, events: dict[type, Event]) -> EventC:
            return EventC()

        # Verify step is properly decorated
        assert is_step_method(join)
        assert is_join_step(join)
        assert get_step_event_types(join) == [EventA, EventB]
        assert get_step_timeout(join) is None
        assert get_step_max_retries(join) == 0
        assert get_step_retry_delay(join) == 1.0

    def test_single_event_metadata_structure(self):
        """Test metadata structure for single-event step."""

        @step(depends_on=EventA, timeout=10.0, max_retries=2)
        async def process(self, ctx: Context, ev: EventA) -> EventB:
            return EventB()

        assert is_step_method(process)
        assert get_step_event_types(process) == [EventA]
        assert is_join_step(process) is False
        assert get_step_timeout(process) == 10.0
        assert get_step_max_retries(process) == 2

    def test_join_step_metadata_structure(self):
        """Test metadata structure for join step."""

        @step(depends_on=[EventA, EventB], timeout=20.0, max_retries=3)
        async def join(self, ctx: Context, events: dict[type, Event]) -> EventC:
            return EventC()

        assert is_step_method(join)
        event_types = get_step_event_types(join)
        assert event_types is not None
        assert set(event_types) == {EventA, EventB}
        assert is_join_step(join) is True
        assert get_step_timeout(join) == 20.0
        assert get_step_max_retries(join) == 3


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_event_in_list(self):
        """Test that single event in list is treated as join."""

        @step(depends_on=[EventA])
        async def process(self, ctx: Context, events: dict[type, Event]) -> EventB:
            return EventB()

        # Single event in list should be treated as join
        assert is_join_step(process) is True
        assert get_step_event_types(process) == [EventA]

    def test_empty_list_rejected(self):
        """Test that empty list is rejected."""
        # Empty list should fail validation (no events to wait for)
        # This will be caught by the Event subclass check
        with pytest.raises(WorkflowValidationError):

            @step(depends_on=[])  # type: ignore
            async def process(self, ctx: Context, events: dict[type, Event]) -> EventB:
                return EventB()

    def test_dict_annotation_without_type_args(self):
        """Test that plain dict annotation is accepted for join."""

        @step(depends_on=[EventA, EventB])
        async def join(self, ctx: Context, events: dict) -> EventC:
            return EventC()

        # Should be valid - plain dict is acceptable
        assert is_join_step(join) is True

    def test_no_type_annotation(self):
        """Test that missing type annotation is accepted."""

        @step(depends_on=[EventA, EventB])
        async def join(self, ctx: Context, events) -> EventC:
            return EventC()

        # Should be valid - annotation is optional


class TestWorkflowValidation:
    """Tests for workflow-level validation."""

    def test_single_start_event_handler_valid(self):
        """Test that workflow with single StartEvent handler is valid."""
        from novastack.workflows import Workflow

        class ValidWorkflow(Workflow):
            @step(depends_on=StartEvent)
            async def start(self, ctx: Context, ev: StartEvent) -> EventA:
                return EventA()

            @step(depends_on=EventA)
            async def process(self, ctx: Context, ev: EventA) -> StopEvent:
                return StopEvent(result="done")

        # Should not raise any errors
        assert ValidWorkflow is not None

    def test_multiple_start_event_handlers_invalid(self):
        """Test that workflow with multiple StartEvent handlers raises validation error."""
        from novastack.workflows import Workflow

        with pytest.raises(WorkflowValidationError) as exc_info:

            class InvalidWorkflow(Workflow):
                @step(depends_on=StartEvent)
                async def start(self, ctx: Context, ev: StartEvent) -> EventA:
                    return EventA()

                @step(depends_on=StartEvent)
                async def start2(self, ctx: Context, ev: StartEvent) -> EventB:
                    return EventB()

                @step(depends_on=EventA)
                async def process(self, ctx: Context, ev: EventA) -> StopEvent:
                    return StopEvent(result="done")

        # Verify error message
        assert "must have exactly one StartEvent handler" in str(exc_info.value)
        assert "start" in str(exc_info.value)
        assert "start2" in str(exc_info.value)

    def test_no_start_event_handler_valid(self):
        """Test that workflow without StartEvent handler is valid (can be a sub-workflow)."""
        from novastack.workflows import Workflow

        class SubWorkflow(Workflow):
            @step(depends_on=EventA)
            async def process(self, ctx: Context, ev: EventA) -> StopEvent:
                return StopEvent(result="done")

        # Should not raise any errors - workflows without StartEvent are valid

    def test_multiple_stop_event_producers_warning(self):
        """Test that workflow with multiple StopEvent producers emits warning."""
        from novastack.workflows import Workflow

        with pytest.warns(UserWarning, match="steps that produce StopEvent"):

            class RaceConditionWorkflow(Workflow):
                @step(depends_on=StartEvent)
                async def start(self, ctx: Context, ev: StartEvent) -> EventA:
                    return EventA()

                @step(depends_on=EventA)
                async def process_a(self, ctx: Context, ev: EventA) -> StopEvent:
                    return StopEvent(result="A")

                @step(depends_on=EventA)
                async def process_b(self, ctx: Context, ev: EventA) -> StopEvent:
                    return StopEvent(result="B")

    def test_single_stop_event_producer_no_warning(self):
        """Test that workflow with single StopEvent producer does not emit warning."""
        import warnings

        from novastack.workflows import Workflow

        # Should not emit warning
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # Turn warnings into errors

            class SafeWorkflow(Workflow):
                @step(depends_on=StartEvent)
                async def start(self, ctx: Context, ev: StartEvent) -> EventA:
                    return EventA()

                @step(depends_on=EventA)
                async def process(self, ctx: Context, ev: EventA) -> StopEvent:
                    return StopEvent(result="done")

        assert SafeWorkflow is not None
