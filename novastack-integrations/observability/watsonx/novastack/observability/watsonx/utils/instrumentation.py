import contextlib
import io
from collections.abc import Callable
from typing import Any


def suppress_output(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    """
    Runs the given function while suppressing all print output (stdout).

    Args:
        fn: The function to run silently.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.

    Returns:
        The return value of the function.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)
