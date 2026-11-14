"""
R5: Fallback model selection — try primary, then fallback, then template tier.
"""

from __future__ import annotations
import logging
from typing import Callable, TypeVar, Any
from app.resilience.retry import retry_with_jitter, is_transient_error
from app.resilience.circuit_breaker import MODEL_CIRCUIT_BREAKER, CircuitBreakerOpenError
from app.resilience.chaos import chaos_maybe_fail, ChaosError
from app.resilience.templates import match_template, TemplatePair

logger = logging.getLogger(__name__)

T = TypeVar("T")


def call_with_fallback(
    primary_fn: Callable[..., T],
    fallback_fn: Callable[..., T] | None = None,
    request_text: str = "",
    *args: Any,
    **kwargs: Any,
) -> tuple[T, str]:
    """
    Try primary model → fallback model → template tier.
    Returns (result, tier_name).
    """
    # Tier 1: Primary model with retry and circuit breaker
    try:
        chaos_maybe_fail()
        result = MODEL_CIRCUIT_BREAKER.call(
            retry_with_jitter(max_retries=2)(primary_fn), *args, **kwargs
        )
        return result, "primary"
    except (ChaosError, CircuitBreakerOpenError, Exception) as e:
        logger.warning(f"Primary model failed: {e}")

    # Tier 2: Fallback model
    if fallback_fn is not None:
        try:
            chaos_maybe_fail()
            result = retry_with_jitter(max_retries=1)(fallback_fn)(*args, **kwargs)
            return result, "fallback"
        except Exception as e:
            logger.warning(f"Fallback model failed: {e}")

    # Tier 3: Template library (deterministic, no model call)
    template = match_template(request_text)
    if template is not None:
        logger.info(f"Using template tier for: {request_text[:50]}")
        return template, "template"  # type: ignore

    # Tier 4: Honest degraded mode
    raise AllTiersExhaustedError(
        "All model tiers failed and no template matches this request. "
        "Cannot generate code right now."
    )


class AllTiersExhaustedError(Exception):
    pass
