import random

from novastack_common.retry.types import RetryState


class _BaseRetryCondition:
    """Base class for retry predicates."""

    def __call__(self, exception: Exception) -> bool:
        raise NotImplementedError


class _BaseStopConditionBase:
    """Base class for stop conditions."""

    def __call__(self, retry_state: RetryState) -> bool:
        raise NotImplementedError


class _BaseWaitStrategy:
    """Base class for wait strategies."""

    def __call__(self, retry_state: RetryState) -> float:
        raise NotImplementedError


class retry_if_exception(_BaseRetryCondition):
    def __call__(self, exception: Exception) -> bool:
        return True


class stop_after_attempt(_BaseStopConditionBase):
    def __init__(self, max_retries: int) -> None:
        if max_retries < 1:
            raise ValueError(
                f"Invalid max_retries '{max_retries}' Input should be: greater than or equal to 1."
            )
        self.max_retries = max_retries

    def __call__(self, retry_state: RetryState) -> bool:
        return retry_state.retry_number >= self.max_retries


class stop_after_delay(_BaseStopConditionBase):
    def __init__(self, max_delay: float) -> None:
        if max_delay < 0:
            raise ValueError(
                f"Invalid max_delay '{max_delay}' Input should be: greater than or equal to 0."
            )
        self.max_delay = max_delay

    def __call__(self, retry_state: RetryState) -> bool:
        return retry_state.elapsed_time >= self.max_delay


class wait_fixed(_BaseWaitStrategy):
    def __init__(self, wait: float) -> None:
        if wait < 0:
            raise ValueError(
                f"Invalid wait '{wait}' Input should be: greater than or equal to 0."
            )
        self.wait = wait

    def __call__(self, retry_state: RetryState) -> float:
        return self.wait


class wait_exponential(_BaseWaitStrategy):
    def __init__(
        self,
        multiplier: float = 1,
        min: float = 0,
        max: float | None = None,
    ) -> None:
        if multiplier < 0:
            raise ValueError(
                f"Invalid multiplier '{multiplier}' Input should be: greater than or equal to 0."
            )
        if min < 0:
            raise ValueError(
                f"Invalid min '{min}' Input should be: greater than or equal to 0."
            )
        if max is not None and max < min:
            raise ValueError(
                f"Invalid max '{max}' Input should be: greater than or equal to min."
            )

        self.multiplier = multiplier
        self.min = min
        self.max = max

    def __call__(self, retry_state: RetryState) -> float:
        delay = self.multiplier * (2 ** (retry_state.retry_number - 1))
        delay = delay if delay > self.min else self.min
        if self.max is not None and delay > self.max:
            delay = self.max
        return delay


class wait_random(_BaseWaitStrategy):
    def __init__(self, min: float, max: float) -> None:
        if min < 0:
            raise ValueError(
                f"Invalid min '{min}' Input should be: greater than or equal to 0."
            )
        if max < min:
            raise ValueError(
                f"Invalid max '{max}' Input should be: greater than or equal to min."
            )

        self.min = min
        self.max = max

    def __call__(self, retry_state: RetryState) -> float:
        return random.uniform(self.min, self.max)
