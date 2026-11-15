"""
R3: Escalation rules — CODE, not the model, decides when to escalate.
Pure Python functions with unit-testable thresholds.
"""

from __future__ import annotations
from app.models import TriageResult, Sentiment, Urgency


# Frustration score weights
SENTIMENT_SCORES = {
    Sentiment.CALM: 0.0,
    Sentiment.FRUSTRATED: 0.4,
    Sentiment.ANGRY: 0.8,
    Sentiment.DESPERATE: 1.0,
}

# Thresholds
FRUSTRATION_ESCALATION_THRESHOLD = 1.0
MAX_POLICY_DENIALS_BEFORE_ESCALATE = 2
MAX_FAILED_REPAIRS_BEFORE_ESCALATE = 2


def compute_frustration_score(current_score: float, triage: TriageResult) -> float:
    """Accumulate frustration across turns. Resets to 0 on calm/positive turns (like ShopBot strikes)."""
    if triage.sentiment in (Sentiment.CALM,):
        return 0.0
    increment = SENTIMENT_SCORES.get(triage.sentiment, 0.0)
    return current_score + increment


def should_escalate(
    triage: TriageResult,
    frustration_score: float,
    policy_denial_count: int,
    failed_repair_count: int,
) -> tuple[bool, str]:
    """
    Rule-based escalation. Returns (should_escalate, reason).
    Code makes this decision, not the model.
    """
    # Rule 1: User explicitly asked for a human
    if triage.wants_human:
        return True, "User explicitly requested human assistance"

    # Rule 2: User is angry (single turn)
    if triage.sentiment == Sentiment.ANGRY:
        return True, "User sentiment is angry"

    if triage.sentiment == Sentiment.DESPERATE:
        return True, "User sentiment is desperate"

    # Rule 3: Accumulated frustration across turns
    if frustration_score >= FRUSTRATION_ESCALATION_THRESHOLD:
        return True, f"Accumulated frustration score ({frustration_score:.1f}) exceeded threshold"

    # Rule 4: Repeated policy denials
    if policy_denial_count >= MAX_POLICY_DENIALS_BEFORE_ESCALATE:
        return True, f"Repeated policy denials ({policy_denial_count})"

    # Rule 5: Repeated failed repairs
    if failed_repair_count >= MAX_FAILED_REPAIRS_BEFORE_ESCALATE:
        return True, f"Repeated failed repair attempts ({failed_repair_count})"

    return False, ""
