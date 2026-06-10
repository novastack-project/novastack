import inspect
from abc import ABC
from typing import Any

from novastack_instrumentation._core import _DISPATCHER_SPAN_DECORATED_ATTR
from novastack_instrumentation.dispatcher import get_dispatcher


class DispatcherSpanMixin(ABC):
    """
    Automatically applies `dispatcher.span` to methods that override decorated methods
    from base classes. This ensures that when you override a method that was decorated
    with `@dispatcher.span` in a parent class, the override will also be automatically
    decorated.
    """

    @staticmethod
    def _is_abstract_method(method: Any) -> bool:
        """Check if a method is abstract."""
        return getattr(method, "__isabstractmethod__", False)

    @staticmethod
    def _is_decorated_method(method: Any) -> bool:
        """Check if a method is decorated with dispatcher.span."""
        return hasattr(method, _DISPATCHER_SPAN_DECORATED_ATTR)

    @classmethod
    def _collect_methods_to_decorate(cls, target_cls: type) -> set[str]:
        """
        Collect method names from base classes that should be decorated
        when overridden in subclasses.

        Only collects methods that were explicitly decorated with @dispatcher.span.
        """
        decorated_methods: set[str] = set()

        # Iterate through base classes (excluding the target class itself)
        for base_cls in inspect.getmro(target_cls)[1:]:
            for attr, method in base_cls.__dict__.items():
                if not callable(method):
                    continue

                # Only collect methods that are already decorated
                if cls._is_decorated_method(method):
                    decorated_methods.add(attr)

        return decorated_methods

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # Collect methods that need decoration from base classes
        methods_to_decorate = cls._collect_methods_to_decorate(cls)

        # Get dispatcher for this module
        dispatcher = get_dispatcher(cls.__module__)

        # Decorate overridden methods in the current class
        for attr, method in cls.__dict__.items():
            # Skip non-callable or abstract methods
            if not callable(method) or cls._is_abstract_method(method):
                continue

            # Decorate if this method overrides a decorated method
            if attr in methods_to_decorate:
                setattr(cls, attr, dispatcher.span(method))
