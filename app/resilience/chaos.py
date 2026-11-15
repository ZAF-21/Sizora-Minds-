"""
R5: Chaos switch — fails 60% of model calls when enabled.
"""

from __future__ import annotations
import random
import logging

logger = logging.getLogger(__name__)

_chaos_enabled = False
_chaos_failure_rate = 0.6


def enable_chaos(failure_rate: float = 0.6) -> None:
    global _chaos_enabled, _chaos_failure_rate
    _chaos_enabled = True
    _chaos_failure_rate = failure_rate
    logger.warning(f"CHAOS MODE ENABLED: {failure_rate*100:.0f}% failure rate")


def disable_chaos() -> None:
    global _chaos_enabled
    _chaos_enabled = False
    logger.info("Chaos mode disabled")


def is_chaos_enabled() -> bool:
    return _chaos_enabled


def chaos_maybe_fail() -> None:
    """Call before each model invocation. Raises if chaos dice says fail."""
    if _chaos_enabled and random.random() < _chaos_failure_rate:
        raise ChaosError("Chaos switch: simulated model failure (429 Too Many Requests)")


class ChaosError(Exception):
    pass
