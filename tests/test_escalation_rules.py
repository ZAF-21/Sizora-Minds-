"""
R3 tests: Escalation rules — unit tests for every escalation rule.
"""

import pytest
from app.escalation.rules import (
    should_escalate, compute_frustration_score,
    FRUSTRATION_ESCALATION_THRESHOLD,
)
from app.escalation.ticket import create_ticket, determine_priority
from app.models import (
    TriageResult, TaskType, Sentiment, Urgency, Priority,
)


def _make_triage(
    sentiment: Sentiment = Sentiment.CALM,
    urgency: Urgency = Urgency.LOW,
    wants_human: bool = False,
) -> TriageResult:
    return TriageResult(
        task_type=TaskType.PYTHON_FUNCTION,
        language="python",
        sentiment=sentiment,
        urgency=urgency,
        wants_human=wants_human,
    )


class TestEscalationRules:
    def test_no_escalation_calm_request(self):
        """A calm request should not escalate."""
        triage = _make_triage(sentiment=Sentiment.CALM)
        escalate, _ = should_escalate(triage, 0.0, 0, 0)
        assert escalate is False

    def test_escalate_wants_human(self):
        """User explicitly asking for human should escalate."""
        triage = _make_triage(wants_human=True)
        escalate, reason = should_escalate(triage, 0.0, 0, 0)
        assert escalate is True
        assert "human" in reason.lower()

    def test_escalate_angry(self):
        """Single angry message should escalate."""
        triage = _make_triage(sentiment=Sentiment.ANGRY)
        escalate, reason = should_escalate(triage, 0.0, 0, 0)
        assert escalate is True

    def test_escalate_desperate(self):
        triage = _make_triage(sentiment=Sentiment.DESPERATE)
        escalate, _ = should_escalate(triage, 0.0, 0, 0)
        assert escalate is True

    def test_escalate_accumulated_frustration(self):
        """Three consecutive frustrated turns should escalate (0.4+0.4+0.4=1.2)."""
        triage1 = _make_triage(sentiment=Sentiment.FRUSTRATED)
        score = compute_frustration_score(0.0, triage1)
        assert score == 0.4
        escalate, _ = should_escalate(triage1, score, 0, 0)
        assert escalate is False

        triage2 = _make_triage(sentiment=Sentiment.FRUSTRATED)
        score = compute_frustration_score(score, triage2)
        assert score == 0.8
        escalate, _ = should_escalate(triage2, score, 0, 0)
        assert escalate is False

        triage3 = _make_triage(sentiment=Sentiment.FRUSTRATED)
        score = compute_frustration_score(score, triage3)
        assert score == pytest.approx(1.2)
        escalate, reason = should_escalate(triage3, score, 0, 0)
        assert escalate is True
        assert "frustration" in reason.lower()

    def test_frustration_resets_on_calm_turn(self):
        """A calm turn resets frustration to 0 — prevents over-escalation."""
        triage_frustrated = _make_triage(sentiment=Sentiment.FRUSTRATED)
        score = compute_frustration_score(0.0, triage_frustrated)
        assert score == 0.4

        triage_calm = _make_triage(sentiment=Sentiment.CALM)
        score = compute_frustration_score(score, triage_calm)
        assert score == 0.0  # Reset!

    def test_escalate_repeated_policy_denials(self):
        triage = _make_triage()
        escalate, reason = should_escalate(triage, 0.0, 2, 0)
        assert escalate is True
        assert "denial" in reason.lower()

    def test_escalate_repeated_failed_repairs(self):
        triage = _make_triage()
        escalate, reason = should_escalate(triage, 0.0, 0, 2)
        assert escalate is True
        assert "repair" in reason.lower()

    def test_no_escalate_one_denial(self):
        triage = _make_triage()
        escalate, _ = should_escalate(triage, 0.0, 1, 0)
        assert escalate is False


class TestTicketCreation:
    def test_p1_ticket_for_pii(self):
        triage = _make_triage()
        priority = determine_priority(triage, has_pii=True)
        assert priority == Priority.P1

    def test_p1_ticket_for_angry(self):
        triage = _make_triage(sentiment=Sentiment.ANGRY)
        priority = determine_priority(triage, has_pii=False)
        assert priority == Priority.P1

    def test_p2_ticket_for_frustrated(self):
        triage = _make_triage(sentiment=Sentiment.FRUSTRATED)
        priority = determine_priority(triage, has_pii=False)
        assert priority == Priority.P2

    def test_p3_ticket_for_calm(self):
        triage = _make_triage()
        priority = determine_priority(triage, has_pii=False)
        assert priority == Priority.P3

    def test_ticket_has_masked_request(self):
        triage = _make_triage(sentiment=Sentiment.ANGRY, wants_human=True)
        ticket = create_ticket(
            user_id="student_c",
            masked_request="[SECRET] THIS IS NOT WORKING!!! get me a human. [AADHAAR]",
            reason="User angry + wants human",
            triage=triage,
            has_pii=True,
        )
        assert ticket.priority == Priority.P1
        assert "[SECRET]" in ticket.handoff_note or "[AADHAAR]" in ticket.handoff_note
        assert "sk-" not in ticket.handoff_note
        assert ticket.sla_minutes == 15
