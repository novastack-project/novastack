import asyncio
import functools
import time
from typing import Any, Callable, TypeVar

from novastack_utils.retry.protocols import (
    RetryCondition,
    RetryState,
    StopCondition,
    WaitStrategy,
)
from novastack_utils.retry.strategies import (
    retry_if_exception,
    stop_after_attempt,
    wait_fixed,
)

T = TypeVar("T")


def _build_retry_state(
    retry_number: int,
    elapsed_time: float,
    last_exception: Exception | None = None,
) -> RetryState:
    return RetryState(
        retry_number=retry_number - 1,
        elapsed_time=elapsed_time,
        last_exception=last_exception,
    )


def retry(
    stop: StopCondition | None = None,
    when: RetryCondition | None = None,
    wait: WaitStrategy | None = None,
    reraise: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T | None]]:
    stop_condition = stop or stop_after_attempt(3)
    retry_condition = when or retry_if_exception()
    wait_strategy = wait or wait_fixed(1)

    def decorator(func: Callable[..., T]) -> Callable[..., T | None]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T | None:
                start_time = time.monotonic()
                retry_number = 0

                while True:
                    retry_number += 1
                    try:
                        return await func(*args, **kwargs)
                    except Exception as exc:
                        retry_state = _build_retry_state(
                            retry_number=retry_number,
                            elapsed_time=time.monotonic() - start_time,
                            last_exception=exc,
                        )

                        if not retry_condition(exc):
                            if reraise:
                                raise
                            return None

                        if stop_condition(retry_state):
                            if reraise:
                                raise
                            return None

                        sleep_time = wait_strategy(retry_state)
                        await asyncio.sleep(sleep_time)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T | None:
            start_time = time.monotonic()
            retry_number = 0

            while True:
                retry_number += 1
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    retry_state = _build_retry_state(
                        retry_number=retry_number,
                        elapsed_time=time.monotonic() - start_time,
                        last_exception=exc,
                    )

                    if not retry_condition(exc):
                        if reraise:
                            raise
                        return None

                    if stop_condition(retry_state):
                        if reraise:
                            raise
                        return None

                    sleep_time = wait_strategy(retry_state)
                    time.sleep(sleep_time)

        return sync_wrapper  # type: ignore[return-value]

    return decorator
