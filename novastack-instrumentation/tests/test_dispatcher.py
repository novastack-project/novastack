import asyncio
import inspect
from asyncio import (
    CancelledError,
)
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from random import random
from typing import Any
from unittest.mock import MagicMock, patch

import novastack_instrumentation as instrument
import pytest
import wrapt
from novastack_instrumentation import DispatcherSpanMixin
from novastack_instrumentation._dispatcher_core import Dispatcher, _context_metadata
from novastack_instrumentation.events import BaseEvent
from novastack_instrumentation.observability import BaseObservability

dispatcher = instrument.get_dispatcher("test")

value_error = ValueError("value error")
cancelled_error = CancelledError("cancelled error")


class _TestStartEvent(BaseEvent):
    @classmethod
    def class_name(cls):
        return "_TestStartEvent"


class _TestEndEvent(BaseEvent):
    @classmethod
    def class_name(cls):
        return "_TestEndEvent"


class _TestEventObservability(BaseObservability):
    events: list[BaseEvent] = []

    @classmethod
    def class_name(cls):
        return "_TestEventObservability"

    def on_event(self, event: BaseEvent, **kwargs: Any) -> Any:
        self.events.append(event)


class _TestAsyncEventObservability(BaseObservability):
    events: list[BaseEvent] = []
    async_calls: int = 0

    @classmethod
    def class_name(cls):
        return "_TestAsyncEventObservability"

    def on_event(self, event: BaseEvent, **kwargs: Any) -> Any:
        self.events.append(event)

    async def ahandle_event(self, event: BaseEvent, **kwargs: Any) -> Any:
        self.async_calls += 1
        await asyncio.sleep(0.01)
        self.events.append(event)
        return None


@dispatcher.span
def func(a, b=3, **kwargs):
    return a + b


@dispatcher.span
async def async_func(a, b=3, **kwargs):
    return a + b


@dispatcher.span
def func_exc(a, b=3, c=4, **kwargs):
    raise value_error


@dispatcher.span
async def async_func_exc(a, b=3, c=4, **kwargs):
    raise cancelled_error


@dispatcher.span
def func_with_event(a, b=3, **kwargs):
    dispatcher.event(_TestStartEvent())


@dispatcher.span
async def async_func_with_event(a, b=3, **kwargs):
    dispatcher.event(_TestStartEvent())
    await asyncio.sleep(0.1)
    dispatcher.event(_TestEndEvent())


class _TestObject:
    @dispatcher.span
    def func(self, a, b=3, **kwargs):
        return a + b

    @dispatcher.span
    async def async_func(self, a, b=3, **kwargs):
        return a + b

    @dispatcher.span
    def func_exc(self, a, b=3, c=4, **kwargs):
        raise value_error

    @dispatcher.span
    async def async_func_exc(self, a, b=3, c=4, **kwargs):
        raise cancelled_error

    @dispatcher.span
    def func_with_event(self, a, b=3, **kwargs):
        dispatcher.event(_TestStartEvent())

    @dispatcher.span
    async def async_func_with_event(self, a, b=3, **kwargs):
        dispatcher.event(_TestStartEvent())
        await asyncio.sleep(0.1)
        await self.async_func(1)  # this should create a new span_id
        # that is fine because we have dispatch_event
        dispatcher.event(_TestEndEvent())

    # Can remove this test once dispatcher.get_dispatch_event is safely dopped.


@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
def test_dispatcher_span_args(mock_uuid, mock_span_start, mock_span_end):
    mock_uuid.uuid4.return_value = "mock"

    result = func(3, c=5)

    span_id = f"{func.__qualname__}-mock"
    bound_args = inspect.signature(func).bind(3, c=5)
    mock_span_start.assert_called_once()
    args, kwargs = mock_span_start.call_args
    assert args == ()
    assert kwargs == {
        "id_": span_id,
        "bound_args": bound_args,
        "instance": None,
        "parent_id": None,
        "metadata": {},
    }

    args, kwargs = mock_span_end.call_args
    assert args == ()
    assert kwargs == {
        "id_": span_id,
        "bound_args": bound_args,
        "instance": None,
        "result": result,
    }


@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
def test_dispatcher_span_args_with_instance(mock_uuid, mock_span_start, mock_span_end):
    mock_uuid.uuid4.return_value = "mock"

    instance = _TestObject()
    result = instance.func(3, c=5)

    span_id = f"{instance.func.__qualname__}-mock"
    bound_args = inspect.signature(instance.func).bind(3, c=5)
    mock_span_start.assert_called_once()
    args, kwargs = mock_span_start.call_args
    assert args == ()
    assert kwargs == {
        "id_": span_id,
        "bound_args": bound_args,
        "instance": instance,
        "parent_id": None,
        "metadata": {},
    }

    args, kwargs = mock_span_end.call_args
    assert args == ()
    assert kwargs == {
        "id_": span_id,
        "bound_args": bound_args,
        "instance": instance,
        "result": result,
    }


@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_exception")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
def test_dispatcher_span_drop_args(
    mock_uuid: MagicMock,
    mock_span_start: MagicMock,
    mock_span_exception: MagicMock,
    mock_span_end: MagicMock,
):
    mock_uuid.uuid4.return_value = "mock"

    instance = _TestObject()
    with pytest.raises(ValueError):
        _ = instance.func_exc(a=3, b=5, c=2, d=5)

    mock_span_start.assert_called_once()

    mock_span_exception.assert_called_once()
    span_id = f"{instance.func_exc.__qualname__}-mock"
    bound_args = inspect.signature(instance.func_exc).bind(a=3, b=5, c=2, d=5)
    args, kwargs = mock_span_exception.call_args
    assert args == ()
    assert kwargs == {
        "id_": span_id,
        "bound_args": bound_args,
        "instance": instance,
        "err": value_error,
    }

    mock_span_end.assert_not_called()


@pytest.mark.asyncio
@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
async def test_dispatcher_async_span_args(mock_uuid, mock_span_start, mock_span_end):
    mock_uuid.uuid4.return_value = "mock"

    result = await async_func(a=3, c=5)

    span_id = f"{async_func.__qualname__}-mock"
    bound_args = inspect.signature(async_func).bind(a=3, c=5)
    mock_span_start.assert_called_once()
    args, kwargs = mock_span_start.call_args
    assert args == ()
    assert kwargs == {
        "id_": span_id,
        "bound_args": bound_args,
        "instance": None,
        "parent_id": None,
        "metadata": {},
    }

    args, kwargs = mock_span_end.call_args
    assert args == ()
    assert kwargs == {
        "id_": span_id,
        "bound_args": bound_args,
        "instance": None,
        "result": result,
    }


@pytest.mark.asyncio
@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
async def test_dispatcher_async_span_args_with_instance(
    mock_uuid, mock_span_start, mock_span_end
):
    mock_uuid.uuid4.return_value = "mock"

    instance = _TestObject()
    result = await instance.async_func(a=3, c=5)

    span_id = f"{instance.async_func.__qualname__}-mock"
    bound_args = inspect.signature(instance.async_func).bind(a=3, c=5)
    mock_span_start.assert_called_once()
    args, kwargs = mock_span_start.call_args
    assert args == ()
    assert kwargs == {
        "id_": span_id,
        "bound_args": bound_args,
        "instance": instance,
        "parent_id": None,
        "metadata": {},
    }

    args, kwargs = mock_span_end.call_args
    assert args == ()
    assert kwargs == {
        "id_": span_id,
        "bound_args": bound_args,
        "instance": instance,
        "result": result,
    }


@pytest.mark.asyncio
@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_exception")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
async def test_dispatcher_async_span_drop_args(
    mock_uuid: MagicMock,
    mock_span_start: MagicMock,
    mock_span_exception: MagicMock,
    mock_span_end: MagicMock,
):
    mock_uuid.uuid4.return_value = "mock"

    with pytest.raises(CancelledError):
        _ = await async_func_exc(a=3, b=5, c=2, d=5)

    mock_span_start.assert_called_once()

    mock_span_exception.assert_called_once()
    span_id = f"{async_func_exc.__qualname__}-mock"
    bound_args = inspect.signature(async_func_exc).bind(a=3, b=5, c=2, d=5)
    args, kwargs = mock_span_exception.call_args
    assert args == ()
    assert kwargs == {
        "id_": span_id,
        "bound_args": bound_args,
        "instance": None,
        "err": cancelled_error,
    }

    mock_span_end.assert_not_called()


@pytest.mark.asyncio
@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_exception")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
async def test_dispatcher_async_span_drop_args_with_instance(
    mock_uuid: MagicMock,
    mock_span_start: MagicMock,
    mock_span_exception: MagicMock,
    mock_span_end: MagicMock,
):
    mock_uuid.uuid4.return_value = "mock"

    instance = _TestObject()
    with pytest.raises(CancelledError):
        _ = await instance.async_func_exc(a=3, b=5, c=2, d=5)

    mock_span_start.assert_called_once()

    mock_span_exception.assert_called_once()
    span_id = f"{instance.async_func_exc.__qualname__}-mock"
    bound_args = inspect.signature(instance.async_func_exc).bind(a=3, b=5, c=2, d=5)
    args, kwargs = mock_span_exception.call_args
    assert args == ()
    assert kwargs == {
        "id_": span_id,
        "bound_args": bound_args,
        "instance": instance,
        "err": cancelled_error,
    }

    mock_span_end.assert_not_called()


@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_exception")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
def test_dispatcher_fire_event(
    mock_uuid: MagicMock,
    mock_span_start: MagicMock,
    mock_span_exception: MagicMock,
    mock_span_end: MagicMock,
):
    mock_uuid.uuid4.return_value = "mock"
    event_handler = _TestEventObservability()
    dispatcher.add_handler(event_handler)

    _ = func_with_event(3, c=5)

    span_id = f"{func_with_event.__qualname__}-mock"
    assert all(e.span_id == span_id for e in event_handler.events)

    mock_span_start.assert_called_once()

    mock_span_exception.assert_not_called()

    mock_span_end.assert_called_once()


@pytest.mark.asyncio
@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_exception")
@patch.object(Dispatcher, "_span_start")
async def test_dispatcher_async_fire_event(
    mock_span_start: MagicMock,
    mock_span_exception: MagicMock,
    mock_span_end: MagicMock,
):
    event_handler = _TestEventObservability()
    dispatcher.add_handler(event_handler)

    tasks = [
        async_func_with_event(a=3, c=5),
        async_func_with_event(5),
        async_func_with_event(4),
    ]
    _ = await asyncio.gather(*tasks)

    span_ids = [e.span_id for e in event_handler.events]
    id_counts = Counter(span_ids)
    assert set(id_counts.values()) == {2}

    assert mock_span_start.call_count == 3

    mock_span_exception.assert_not_called()

    assert mock_span_end.call_count == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("use_async", [True, False])
@patch.object(Dispatcher, "_span_start")
async def test_dispatcher_attaches_tags_to_events_and_spans(
    mock_span_start: MagicMock,
    use_async: bool,
):
    event_handler = _TestEventObservability()
    dispatcher.add_handler(event_handler)
    test_tags = {"test_tag_key": "test_tag_value"}

    with _context_metadata(test_tags):
        if use_async:
            await async_func_with_event(a=3, c=5)
        else:
            func_with_event(a=3, c=5)

    mock_span_start.assert_called_once()
    assert mock_span_start.call_args[1]["metadata"] == test_tags
    assert all(e.metadata == test_tags for e in event_handler.events)


@patch.object(Dispatcher, "_span_start")
def test_dispatcher_attaches_tags_to_concurrent_events(
    mock_span_start: MagicMock,
):
    event_handler = _TestEventObservability()
    dispatcher.add_handler(event_handler)

    num_functions = 5
    test_tags = [{"test_tag_key": num} for num in range(num_functions)]
    test_tags_set = {str(tag) for tag in test_tags}

    def run_func_with_tags(tag):
        with _context_metadata(tag):
            func_with_event(3, c=5)

    futures = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        for tag in test_tags:
            futures.append(executor.submit(run_func_with_tags, tag))

    for future in futures:
        future.result()

    assert len(mock_span_start.call_args_list) == num_functions
    assert len(event_handler.events) == num_functions
    actual_span_tags = {
        str(call_kwargs["metadata"])
        for _, call_kwargs in mock_span_start.call_args_list
    }
    actual_event_tags = {str(e.metadata) for e in event_handler.events}
    assert actual_span_tags == test_tags_set
    assert actual_event_tags == test_tags_set


@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_exception")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
def test_dispatcher_fire_event_with_instance(
    mock_uuid, mock_span_start, mock_span_exception, mock_span_end
):
    mock_uuid.uuid4.return_value = "mock"
    event_handler = _TestEventObservability()
    dispatcher.add_handler(event_handler)

    instance = _TestObject()
    _ = instance.func_with_event(a=3, c=5)

    span_id = f"{instance.func_with_event.__qualname__}-mock"
    assert all(e.span_id == span_id for e in event_handler.events)

    mock_span_start.assert_called_once()

    mock_span_exception.assert_not_called()

    mock_span_end.assert_called_once()


@pytest.mark.asyncio
@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_exception")
@patch.object(Dispatcher, "_span_start")
async def test_dispatcher_async_fire_event_with_instance(
    mock_span_start: MagicMock,
    mock_span_exception: MagicMock,
    mock_span_end: MagicMock,
):
    event_handler = _TestEventObservability()
    dispatcher.add_handler(event_handler)

    instance = _TestObject()
    tasks = [
        instance.async_func_with_event(a=3, c=5),
        instance.async_func_with_event(5),
    ]
    _ = await asyncio.gather(*tasks)

    span_ids = [e.span_id for e in event_handler.events]
    id_counts = Counter(span_ids)
    assert set(id_counts.values()) == {2}

    assert mock_span_start.call_count == 4

    mock_span_exception.assert_not_called()

    assert mock_span_end.call_count == 4


@patch.object(Dispatcher, "_span_start")
def test_span_decorator_is_idempotent(mock_span_start):
    x, z = random(), dispatcher.span
    assert z(z(z(lambda: x)))() == x
    mock_span_start.assert_called_once()


@patch.object(Dispatcher, "_span_start")
def test_span_decorator_is_idempotent_with_pass_through(mock_span_start):
    x, z = random(), dispatcher.span
    a, b, c, d = (wrapt.decorator(lambda f, *_: f()) for _ in range(4))
    assert z(a(b(z(c(d(z(lambda: x)))))))() == x
    mock_span_start.assert_called_once()


@patch.object(Dispatcher, "_span_start")
def test_mixin_decorates_overridden_method(mock_span_start):
    x, z = random(), dispatcher.span
    A = type("A", (DispatcherSpanMixin,), {"f": z(lambda _: x)})
    B = type("B", (A,), {"f": lambda _: x + 1})
    C = type("C", (B,), {"f": lambda _: x + 2})
    D = type("D", (C, B), {"f": lambda _: x + 3})
    for i, T in enumerate((A, B, C, D)):
        assert T().f() - i == pytest.approx(x)  # type:ignore
        assert mock_span_start.call_count - i == 1


@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
def test_span_naming_with_inheritance(mock_uuid, mock_span_start, mock_span_end):
    """Test that span IDs use the runtime class name, not the definition class name."""
    mock_uuid.uuid4.return_value = "mock"

    class BaseClass:
        @dispatcher.span
        def base_method(self, x):
            return x * 2

        @dispatcher.span
        async def async_base_method(self, x):
            return x * 3

    class DerivedClass(BaseClass):
        pass

    class AnotherDerivedClass(BaseClass):
        @dispatcher.span
        def derived_method(self, x):
            return x * 4

    base_instance = BaseClass()
    derived_instance = DerivedClass()
    another_derived_instance = AnotherDerivedClass()

    base_result = base_instance.base_method(5)
    derived_result = derived_instance.base_method(5)
    another_derived_result = another_derived_instance.derived_method(5)

    assert mock_span_start.call_count == 3

    calls = mock_span_start.call_args_list

    assert calls[0][1]["id_"] == "BaseClass.base_method-mock"

    assert calls[1][1]["id_"] == "DerivedClass.base_method-mock"

    assert calls[2][1]["id_"] == "AnotherDerivedClass.derived_method-mock"


@pytest.mark.asyncio
@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
async def test_async_span_naming_with_inheritance(
    mock_uuid, mock_span_start, mock_span_end
):
    """Test that async span IDs use the runtime class name, not the definition class name."""
    mock_uuid.uuid4.return_value = "mock"

    class BaseClass:
        @dispatcher.span
        async def async_base_method(self, x):
            return x * 3

    class DerivedClass(BaseClass):
        pass

    base_instance = BaseClass()
    derived_instance = DerivedClass()

    base_result = await base_instance.async_base_method(5)
    derived_result = await derived_instance.async_base_method(5)

    assert mock_span_start.call_count == 2

    calls = mock_span_start.call_args_list

    assert calls[0][1]["id_"] == "BaseClass.async_base_method-mock"

    assert calls[1][1]["id_"] == "DerivedClass.async_base_method-mock"


@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
def test_span_naming_regular_functions_unchanged(
    mock_uuid, mock_span_start, mock_span_end
):
    """Test that regular functions (non-methods) still use __qualname__."""
    mock_uuid.uuid4.return_value = "mock"

    @dispatcher.span
    def regular_function(x):
        return x * 5

    result = regular_function(10)

    mock_span_start.assert_called_once()
    call_kwargs = mock_span_start.call_args[1]

    assert call_kwargs["id_"] == f"{regular_function.__qualname__}-mock"


@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
def test_span_naming_complex_inheritance(mock_uuid, mock_span_start, mock_span_end):
    """Test span naming with multiple levels of inheritance."""
    mock_uuid.uuid4.return_value = "mock"

    class GrandParent:
        @dispatcher.span
        def shared_method(self, x):
            return x

    class Parent(GrandParent):
        pass

    class Child(Parent):
        @dispatcher.span
        def child_method(self, x):
            return x * 2

    class GrandChild(Child):
        pass

    instances = [GrandParent(), Parent(), Child(), GrandChild()]

    for instance in instances:
        instance.shared_method(1)

    instances[2].child_method(1)
    instances[3].child_method(1)

    assert mock_span_start.call_count == 6

    calls = mock_span_start.call_args_list

    assert calls[0][1]["id_"] == "GrandParent.shared_method-mock"
    assert calls[1][1]["id_"] == "Parent.shared_method-mock"
    assert calls[2][1]["id_"] == "Child.shared_method-mock"
    assert calls[3][1]["id_"] == "GrandChild.shared_method-mock"

    assert calls[4][1]["id_"] == "Child.child_method-mock"
    assert calls[5][1]["id_"] == "GrandChild.child_method-mock"


@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
def test_span_naming_with_method_override(mock_uuid, mock_span_start, mock_span_end):
    """Test span naming when methods are overridden in derived classes."""
    mock_uuid.uuid4.return_value = "mock"

    class Base:
        @dispatcher.span
        def method(self, x):
            return x

    class Derived(Base):
        @dispatcher.span
        def method(self, x):
            return x * 2

    base_instance = Base()
    derived_instance = Derived()

    base_instance.method(1)
    derived_instance.method(1)

    assert mock_span_start.call_count == 2

    calls = mock_span_start.call_args_list

    assert calls[0][1]["id_"] == "Base.method-mock"
    assert calls[1][1]["id_"] == "Derived.method-mock"


@patch.object(Dispatcher, "_span_end")
@patch.object(Dispatcher, "_span_start")
@patch("novastack_instrumentation._dispatcher_core.uuid")
def test_span_naming_with_nested_classes(mock_uuid, mock_span_start, mock_span_end):
    """Test span naming with nested classes."""
    mock_uuid.uuid4.return_value = "mock"

    class Outer:
        class Inner:
            @dispatcher.span
            def inner_method(self, x):
                return x

        @dispatcher.span
        def outer_method(self, x):
            return x * 2

    outer_instance = Outer()
    inner_instance = Outer.Inner()

    outer_instance.outer_method(1)
    inner_instance.inner_method(1)

    assert mock_span_start.call_count == 2

    calls = mock_span_start.call_args_list

    assert calls[0][1]["id_"] == "Outer.outer_method-mock"
    assert calls[1][1]["id_"] == "Inner.inner_method-mock"
