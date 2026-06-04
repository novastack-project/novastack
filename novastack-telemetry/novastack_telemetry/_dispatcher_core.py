import asyncio
import inspect
import logging
import uuid
from contextlib import contextmanager
from contextvars import Context, ContextVar, Token, copy_context
from functools import partial
from typing import Any, Callable, Generator, Optional, TypeVar

import wrapt
from pydantic import BaseModel, Field

from novastack_telemetry.events import BaseEvent, SpanExceptionEvent
from novastack_telemetry.observability import BaseObservability
from novastack_telemetry.span import _active_span_id

_CONTEXT_METADATA_KEY = "context_metadata"
_DISPATCHER_SPAN_DECORATED_ATTR = "__dispatcher_span_decorated__"

_logger = logging.getLogger(__name__)

# ContextVar for managing active context metadata
_active_context_metadata: ContextVar[dict[str, Any]] = ContextVar(
    "_context_metadata", default={}
)
_R = TypeVar("_R")


@contextmanager
def _context_metadata(new_metadata: dict[str, Any]) -> Generator[None, None, None]:
    token = _active_context_metadata.set(new_metadata)
    try:
        yield
    finally:
        _active_context_metadata.reset(token)


class Dispatcher(BaseModel):
    """
    Orchestrates telemetry events and span lifecycle management.

    Routes events and span signals to registered handlers through a hierarchical
    propagation chain. Provides a decorator-based API (@dispatcher.span) for
    automatic span tracking in both sync and async contexts. Supports thread-safe
    and async-safe operations using ContextVars, with automatic parent-child span
    relationships, trace context management, and silent exception handling to
    prevent telemetry failures from affecting application code.
    """

    model_config = {"arbitrary_types_allowed": True}
    name: str = Field(default_factory=str, description="The name of dispatcher")
    handlers: list[BaseObservability] = Field(
        default=[], description="List of unified handlers"
    )
    parent_name: str = Field(
        default_factory=str, description="The name of parent Dispatcher."
    )
    dispatcher_manager: Optional["_DispatcherManager"] = Field(
        default=None, description="Dispatcher manager."
    )
    root_name: str = Field(
        default="root", description="The name of Dispatcher root tree."
    )
    propagate: bool = Field(
        default=True,
        description="Whether to propagate the event to parent dispatchers and their handlers",
    )

    @property
    def parent(self) -> "Dispatcher":
        assert self.dispatcher_manager is not None
        return self.dispatcher_manager.dispatchers[self.parent_name]

    @property
    def root(self) -> "Dispatcher":
        assert self.dispatcher_manager is not None
        return self.dispatcher_manager.dispatchers[self.root_name]

    def _get_handler_hierarchy(self) -> Generator[BaseObservability, None, None]:
        """Retrieve every handlers reachable via the propagation chain."""
        h: Dispatcher | None = self
        while h:
            yield from h.handlers
            if not h.propagate:
                break
            h = h.parent

    def _dispatch_to_handlers(
        self, handler_method: str, *args: Any, **kwargs: Any
    ) -> None:
        """
        Invoke handler method across the propagation chain with error isolation.

        Calls the specified method on all handlers in the chain. Handler exceptions
        are silently caught to ensure telemetry failures don't break application code.

        Args:
            handler_method: Name of the handler method to call
            *args: Positional arguments to pass to the handler method
            **kwargs: Keyword arguments to pass to the handler method
        """
        for h in self._get_handler_hierarchy():
            try:
                getattr(h, handler_method)(*args, **kwargs)
            except BaseException:
                pass

    def add_handler(self, handler: BaseObservability) -> None:
        """Add handler to set of handlers."""
        self.handlers += [handler]

    def event(self, event: BaseEvent, **kwargs: Any) -> None:
        """Dispatch event to all registered handlers."""
        event.metadata.update(_active_context_metadata.get())
        self._dispatch_to_handlers("on_event", event, **kwargs)

    def _span_start(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        parent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Internal: Send notice to handlers that a span with id_ has started."""
        self._dispatch_to_handlers(
            "on_span_start",
            id_=id_,
            bound_args=bound_args,
            instance=instance,
            parent_id=parent_id,
            metadata=metadata,
            **kwargs,
        )

    def _span_end(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        result: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Internal: Send notice to handlers that a span with id_ is exiting."""
        self._dispatch_to_handlers(
            "on_span_end",
            id_=id_,
            bound_args=bound_args,
            instance=instance,
            result=result,
            **kwargs,
        )

    def _span_exception(
        self,
        id_: str,
        bound_args: inspect.BoundArguments,
        instance: Any | None = None,
        err: BaseException | None = None,
        **kwargs: Any,
    ) -> None:
        """Internal: Send notice to handlers that a span with id_ is being exited due an exception."""
        self._dispatch_to_handlers(
            "on_span_exception",
            id_=id_,
            bound_args=bound_args,
            instance=instance,
            err=err,
            **kwargs,
        )

    def capture_propagation_context(self) -> dict[str, Any]:
        """
        Capture trace propagation context from all handlers and active metadata.

        Returns a serializable dictionary with namespaced handler data and context
        metadata, suitable for cross-process propagation via restore_propagation_context().
        """
        result: dict[str, Any] = {}
        for h in self._get_handler_hierarchy():
            try:
                result.update(h.capture_propagation_context())
            except BaseException:
                _logger.warning("Error capturing propagation context", exc_info=True)
        metadata = _active_context_metadata.get()
        if metadata:
            result[_CONTEXT_METADATA_KEY] = dict(metadata)
        return result

    def restore_propagation_context(self, context: dict[str, Any]) -> None:
        """
        Restore trace propagation context across all handlers and metadata.

        Applies the context to all handlers in the chain and updates active
        context metadata for subsequent span operations.
        """
        for h in self._get_handler_hierarchy():
            try:
                h.restore_propagation_context(context)
            except BaseException:
                _logger.warning("Error restoring propagation context", exc_info=True)
        metadata = context.get(_CONTEXT_METADATA_KEY)
        if metadata:
            _active_context_metadata.set(dict(metadata))

    def shutdown(self) -> None:
        """
        Gracefully shutdown all handlers in the propagation chain.

        Invokes shutdown() on each handler while suppressing exceptions to ensure
        complete cleanup even if individual handler fail.
        """
        for h in self._get_handler_hierarchy():
            try:
                h.shutdown()
            except BaseException:
                _logger.warning("Error closing handler %s", h, exc_info=True)

    def span(self, func: Callable[..., _R]) -> Callable[..., _R]:
        try:
            if hasattr(func, _DISPATCHER_SPAN_DECORATED_ATTR):
                return func
            setattr(func, _DISPATCHER_SPAN_DECORATED_ATTR, True)
        except AttributeError:
            pass

        @wrapt.decorator
        def wrapper(func: Callable, instance: Any, args: list, kwargs: dict) -> Any:
            bound_args = inspect.signature(func).bind(*args, **kwargs)
            if instance is not None:
                actual_class = type(instance).__name__
                method_name = func.__name__
                id_ = f"{actual_class}.{method_name}-{uuid.uuid4()}"
            else:
                id_ = f"{func.__qualname__}-{uuid.uuid4()}"
            metadata = _active_context_metadata.get()
            result = None

            # Copy the current context
            context = copy_context()

            token = _active_span_id.set(id_)
            parent_id = None if token.old_value is Token.MISSING else token.old_value
            self._span_start(
                id_=id_,
                bound_args=bound_args,
                instance=instance,
                parent_id=parent_id,
                metadata=metadata,
            )

            def handle_future_result(
                future: asyncio.Future,
                span_id: str,
                bound_args: inspect.BoundArguments,
                instance: Any,
                context: Context,
            ) -> None:
                try:
                    result = None if future.exception() else future.result()

                    self._span_end(
                        id_=span_id,
                        bound_args=bound_args,
                        instance=instance,
                        result=result,
                    )
                    return result
                except BaseException as e:
                    self.event(SpanExceptionEvent(span_id=span_id, err_str=str(e)))
                    self._span_exception(
                        id_=span_id, bound_args=bound_args, instance=instance, err=e
                    )
                    raise
                finally:
                    try:
                        context.run(_active_span_id.reset, token)
                    except ValueError as e:
                        _logger.debug(f"Failed to reset _active_span_id: {e}")

            try:
                result = func(*args, **kwargs)
                if isinstance(result, asyncio.Future):
                    new_future = asyncio.ensure_future(result)
                    new_future.add_done_callback(
                        partial(
                            handle_future_result,
                            span_id=id_,
                            bound_args=bound_args,
                            instance=instance,
                            context=context,
                        )
                    )
                    return new_future
                else:
                    self._span_end(
                        id_=id_, bound_args=bound_args, instance=instance, result=result
                    )
                    return result
            except BaseException as e:
                self.event(SpanExceptionEvent(span_id=id_, err_str=str(e)))
                self._span_exception(
                    id_=id_, bound_args=bound_args, instance=instance, err=e
                )
                raise
            finally:
                if not isinstance(result, asyncio.Future):
                    _active_span_id.reset(token)

        @wrapt.decorator
        async def async_wrapper(
            func: Callable, instance: Any, args: list, kwargs: dict
        ) -> Any:
            bound_args = inspect.signature(func).bind(*args, **kwargs)
            if instance is not None:
                actual_class = type(instance).__name__
                method_name = func.__name__
                id_ = f"{actual_class}.{method_name}-{uuid.uuid4()}"
            else:
                id_ = f"{func.__qualname__}-{uuid.uuid4()}"
            metadata = _active_context_metadata.get()

            token = _active_span_id.set(id_)
            parent_id = None if token.old_value is Token.MISSING else token.old_value
            self._span_start(
                id_=id_,
                bound_args=bound_args,
                instance=instance,
                parent_id=parent_id,
                metadata=metadata,
            )
            try:
                result = await func(*args, **kwargs)
            except BaseException as e:
                self.event(SpanExceptionEvent(span_id=id_, err_str=str(e)))
                self._span_exception(
                    id_=id_, bound_args=bound_args, instance=instance, err=e
                )
                raise
            else:
                self._span_end(
                    id_=id_, bound_args=bound_args, instance=instance, result=result
                )
                return result
            finally:
                _active_span_id.reset(token)

        if inspect.iscoroutinefunction(func):
            return async_wrapper(func)  # type: ignore
        else:
            return wrapper(func)  # type: ignore

    @property
    def log_name(self) -> str:
        if self.parent:
            return f"{self.parent.name}.{self.name}"
        else:
            return self.name


class _DispatcherManager:
    def __init__(self, root: Dispatcher) -> None:
        self.dispatchers: dict[str, Dispatcher] = {root.name: root}

    def add_dispatcher(self, d: Dispatcher) -> None:
        self.dispatchers.setdefault(d.name, d)


Dispatcher.model_rebuild()
