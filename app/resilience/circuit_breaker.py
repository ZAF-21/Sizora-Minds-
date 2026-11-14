"""
R5: Circuit breaker — stops calling a failing service after repeated failures.
"""

from __future__ import annotations
import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal: requests pass through
    OPEN = "open"           # Tripped: requests fail fast
    HALF_OPEN = "half_open" # Testing: one request allowed


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    _failure_count: int = 0
    _last_failure_time: float = 0.0
    _state: CircuitState = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        state = self.state

        if state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN. Retry after {self.recovery_timeout}s"
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self._failure_count} failures")

    def reset(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time = 0.0


class CircuitBreakerOpenError(Exception):
    pass


MODEL_CIRCUIT_BREAKER = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
