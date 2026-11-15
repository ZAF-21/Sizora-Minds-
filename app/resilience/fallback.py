"""
R5: Fallback model selection — try primary, then fallback, then template tier.
Tracks what happened so the UI can show it.
"""

from __future__ import annotations
import logging
import time
from typing import Callable, TypeVar, Any
from app.resilience.retry import retry_with_jitter, is_transient_error
from app.resilience.circuit_breaker import MODEL_CIRCUIT_BREAKER, CircuitBreakerOpenError
from app.resilience.chaos import chaos_maybe_fail, ChaosError
from app.resilience.templates import match_template, TemplatePair

logger = logging.getLogger(__name__)

T = TypeVar("T")

_last_attempt_log: list[str] = []


def get_attempt_log() -> list[str]:
    return list(_last_attempt_log)


def call_with_fallback(
    primary_fn: Callable[..., T],
    fallback_fn: Callable[..., T] | None = None,
    request_text: str = "",
    *args: Any,
    **kwargs: Any,
) -> tuple[T, str]:
    """
    Try primary model -> fallback model -> template tier.
    Returns (result, tier_name). Logs each attempt for UI visibility.
    """
    _last_attempt_log.clear()

    # Tier 1: Primary model with retry and circuit breaker
    try:
        chaos_maybe_fail()
        _last_attempt_log.append("Primary model: attempting...")
        result = MODEL_CIRCUIT_BREAKER.call(
            retry_with_jitter(max_retries=2)(primary_fn), *args, **kwargs
        )
        _last_attempt_log.append("Primary model: success")
        return result, "primary"
    except ChaosError:
        _last_attempt_log.append("Primary model: failed (429 Too Many Requests)")
    except CircuitBreakerOpenError:
        _last_attempt_log.append("Primary model: skipped (circuit breaker open — too many recent failures)")
    except Exception as e:
        _last_attempt_log.append(f"Primary model: failed ({type(e).__name__})")

    # Tier 2: Fallback model
    if fallback_fn is not None:
        try:
            chaos_maybe_fail()
            _last_attempt_log.append("Fallback model: attempting...")
            result = retry_with_jitter(max_retries=1)(fallback_fn)(*args, **kwargs)
            _last_attempt_log.append("Fallback model: success")
            return result, "fallback"
        except ChaosError:
            _last_attempt_log.append("Fallback model: failed (429 Too Many Requests)")
        except Exception as e:
            _last_attempt_log.append(f"Fallback model: failed ({type(e).__name__})")

    # Tier 3: Template library (deterministic, no model call)
    template = match_template(request_text)
    if template is not None:
        _last_attempt_log.append("Template library: matched — serving verified code")
        return template, "template"  # type: ignore

    # Tier 4: Honest degraded mode
    _last_attempt_log.append("All tiers exhausted — no answer available")
    raise AllTiersExhaustedError(
        "All model tiers failed and no template matches this request. "
        "Cannot generate code right now."
    )


class AllTiersExhaustedError(Exception):
    pass
