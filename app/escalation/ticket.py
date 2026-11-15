"""
R3: Escalation ticket — carries priority, SLA, and a handoff note.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from app.models import (
    EscalationTicket, Priority, Sentiment, Urgency, TriageResult,
)


# SLA in minutes by priority
SLA_MAP = {
    Priority.P1: 15,
    Priority.P2: 60,
    Priority.P3: 240,
}


def determine_priority(triage: TriageResult, has_pii: bool) -> Priority:
    """Determine ticket priority from triage signals."""
    if has_pii:
        return Priority.P1
    if triage.sentiment in (Sentiment.ANGRY, Sentiment.DESPERATE):
        return Priority.P1
    if triage.urgency in (Urgency.CRITICAL, Urgency.HIGH):
        return Priority.P1
    if triage.sentiment == Sentiment.FRUSTRATED:
        return Priority.P2
    if triage.urgency == Urgency.MEDIUM:
        return Priority.P2
    return Priority.P3


def create_ticket(
    user_id: str,
    masked_request: str,
    reason: str,
    triage: TriageResult,
    has_pii: bool = False,
    attempts: int = 0,
    last_failing_test: str = "",
) -> EscalationTicket:
    """Create an escalation ticket with all context for the human agent."""
    priority = determine_priority(triage, has_pii)

    handoff_note = f"Request: {masked_request}\n"
    if attempts > 0:
        handoff_note += f"Attempts: {attempts}\n"
    if last_failing_test:
        handoff_note += f"Last failing test: {last_failing_test}\n"

    return EscalationTicket(
        ticket_id=f"TKT-{uuid.uuid4().hex[:8].upper()}",
        user_id=user_id,
        priority=priority,
        sla_minutes=SLA_MAP[priority],
        reason=reason,
        handoff_note=handoff_note,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
