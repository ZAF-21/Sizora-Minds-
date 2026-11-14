"""
R5: Retry with full-jitter backoff — only for transient errors (429, 5xx, timeout).
"""

from __future__ import annotations
import random
import time
import logging
from functools import wraps
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
BASE_DELAY = 1.0
MAX_DELAY = 30.0


def is_transient_error(exc: Exception) -> bool:
    """Check if an exception is a transient error worth retrying."""
    exc_str = str(exc).lower()
    if any(code_str in exc_str for code_str in ["429", "500", "502", "503", "504"]):
        return True
    if "timeout" in exc_str or "timed out" in exc_str:
        return True
    if "rate limit" in exc_str or "too many requests" in exc_str:
        return True
    if "connection" in exc_str and ("reset" in exc_str or "refused" in exc_str):
        return True
    return False


def full_jitter_delay(attempt: int, base: float = BASE_DELAY, cap: float = MAX_DELAY) -> float:
    """Calculate delay with full jitter: random between 0 and min(cap, base * 2^attempt)."""
    exp_delay = min(cap, base * (2 ** attempt))
    return random.uniform(0, exp_delay)


def retry_with_jitter(max_retries: int = 3, base: float = BASE_DELAY, cap: float = MAX_DELAY):
    """Decorator: retry transient errors with full-jitter backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if not is_transient_error(exc) or attempt == max_retries:
                        raise
                    delay = full_jitter_delay(attempt, base, cap)
                    logger.warning(
                        f"Retry {attempt+1}/{max_retries} for {func.__name__} "
                        f"after {delay:.2f}s: {exc}"
                    )
                    time.sleep(delay)
            raise last_exc  # type: ignore
        return wrapper
    return decorator
