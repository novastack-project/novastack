from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class RetryState:
    retry_number: int
    elapsed_time: float
    last_exception: Exception | None = None


class RetryCondition(Protocol):
    """Protocol for retry predicates that decide whether an exception is retryable."""

    def __call__(self, exception: Exception) -> bool: ...


class StopCondition(Protocol):
    """Protocol for stop conditions that decide when to stop retrying."""

    def __call__(self, retry_state: RetryState) -> bool: ...


class WaitStrategy(Protocol):
    """Protocol for wait strategies that determine how long to wait between retries."""

    def __call__(self, retry_state: RetryState) -> float: ...
