import pytest
from novastack_utils.retry import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_fixed,
    wait_random,
)


def test_retry_success():
    """Test retry decorator with successful function."""

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.01))
    def successful_func():
        return "success"

    result = successful_func()
    assert result == "success"


def test_retry_with_exception():
    """Test retry decorator with function that fails then succeeds."""
    attempt_count = {"count": 0}

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.01))
    def failing_func():
        attempt_count["count"] += 1
        if attempt_count["count"] < 3:
            raise ValueError("Test error")
        return "success"

    result = failing_func()
    assert result == "success"
    assert attempt_count["count"] == 3


def test_retry_exhausted():
    """Test retry decorator when retries are exhausted."""

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(0.01), reraise=False)
    def always_fails():
        raise ValueError("Always fails")

    result = always_fails()
    assert result is None


@pytest.mark.asyncio
async def test_retry_async():
    """Test retry decorator with async function."""

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.01))
    async def async_func():
        return "async success"

    result = await async_func()
    assert result == "async success"


def test_retry_if_exception():
    """Test retry_if_exception strategy."""
    strategy = retry_if_exception()
    assert strategy(ValueError("test")) is True
    assert strategy(Exception("test")) is True


def test_stop_after_attempt():
    """Test stop_after_attempt strategy."""
    from novastack_utils.retry.types import RetryState

    strategy = stop_after_attempt(3)
    state = RetryState(
        retry_number=2,
        elapsed_time=1.0,
    )
    assert strategy(state) is False

    state = RetryState(
        retry_number=3,
        elapsed_time=1.0,
    )
    assert strategy(state) is True


def test_stop_after_delay():
    """Test stop_after_delay strategy."""
    from novastack_utils.retry.types import RetryState

    strategy = stop_after_delay(2.0)
    state = RetryState(
        retry_number=0,
        elapsed_time=1.0,
    )
    assert strategy(state) is False

    state = RetryState(
        retry_number=1,
        elapsed_time=3.0,
    )
    assert strategy(state) is True


def test_wait_fixed():
    """Test wait_fixed strategy."""
    from novastack_utils.retry.types import RetryState

    strategy = wait_fixed(2.0)
    state = RetryState(
        retry_number=0,
        elapsed_time=0.0,
    )
    assert strategy(state) == 2.0


def test_wait_exponential():
    """Test wait_exponential strategy."""
    from novastack_utils.retry.types import RetryState

    strategy = wait_exponential(multiplier=1, min=0, max=10)

    state = RetryState(
        retry_number=0,
        elapsed_time=0.0,
    )
    assert strategy(state) == 0.5

    state = RetryState(
        retry_number=1,
        elapsed_time=0.0,
    )
    assert strategy(state) == 1.0  # 2^1 * 1 = 1


def test_wait_random():
    """Test wait_random strategy."""
    from novastack_utils.retry.types import RetryState

    strategy = wait_random(1.0, 3.0)
    state = RetryState(
        retry_number=0,
        elapsed_time=0.0,
    )
    wait_time = strategy(state)
    assert 1.0 <= wait_time <= 3.0
