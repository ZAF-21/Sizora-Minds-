"""
End-to-end integration tests — chains multiple CodeForge components together
to prove the pipeline works, not just individual functions.
"""

import pytest
from app.security.privacy import mask_pii, has_pii, _luhn_ok
from app.execution.policy import evaluate_code_policy
from app.execution.sandbox import run_in_sandbox
from app.execution.idempotency import IdempotencyStore
from app.escalation.rules import should_escalate, compute_frustration_score
from app.escalation.ticket import create_ticket
from app.resilience.templates import match_template
from app.models import (
    PolicyVerdict, TriageResult, TaskType, Sentiment, Urgency,
)


class TestLuhnValidation:
    """Luhn check prevents false positives on order reference numbers."""

    def test_luhn_valid_card(self):
        assert _luhn_ok("4111111111111111") is True

    def test_luhn_invalid_card(self):
        assert _luhn_ok("4111111111111112") is False

    def test_valid_card_masked(self):
        assert "[CARD]" in mask_pii("My card is 4111 1111 1111 1111")

    def test_invalid_card_not_masked(self):
        text = "Reference 4111 1111 1111 1112"
        assert "[CARD]" not in mask_pii(text)

    def test_order_reference_survives(self):
        text = "Order ref: 1234567890123456"
        masked = mask_pii(text)
        assert "1234567890123456" in masked or "[CARD]" not in masked


class TestEndToEndPipeline:
    """Chains guard_in → policy → sandbox to prove the full flow works."""

    def test_safe_code_through_full_pipeline(self):
        request = "Write a function that adds two numbers"
        masked = mask_pii(request)
        assert masked == request

        code = "def add(a: int, b: int) -> int:\n    return a + b"
        tests = "from solution import add\n\ndef test_add_basic():\n    assert add(1, 2) == 3\n\ndef test_add_negative():\n    assert add(-1, 1) == 0\n"

        policy = evaluate_code_policy(code)
        assert policy.verdict == PolicyVerdict.ALLOW

        result = run_in_sandbox(code, tests)
        assert result["passed"] is True
        assert result["exit_code"] == 0

    def test_dangerous_code_blocked_at_policy(self):
        code = "import os\nimport shutil\nshutil.rmtree(os.path.expanduser('~'))"
        policy = evaluate_code_policy(code)
        assert policy.verdict == PolicyVerdict.DENY

    def test_pii_masked_before_reaching_pipeline(self):
        raw = "sk-abc123456789012345678901 fix my code please. Call me at +91 98765 43210"
        masked = mask_pii(raw)
        assert "sk-abc" not in masked
        assert "[SECRET]" in masked
        assert "[PHONE]" in masked

    def test_template_fallback_produces_passing_tests(self):
        template = match_template("Write a palindrome checker")
        assert template is not None

        result = run_in_sandbox(template.code, template.tests)
        assert result["passed"] is True
        assert result["exit_code"] == 0

    def test_idempotent_execution(self):
        store = IdempotencyStore()
        key = IdempotencyStore.make_key("student_a", "def f(): pass", "def test_f(): pass")

        assert store.has(key) is False
        store.store(key, "mock_report")
        assert store.has(key) is True
        assert store.get(key) == "mock_report"

    def test_escalation_with_pii_produces_clean_ticket(self):
        raw = "sk-secret123456789012345678 THIS IS NOT WORKING!!! get me a human. My Aadhaar is 1234 5678 9012"
        masked = mask_pii(raw)

        assert "sk-secret" not in masked
        assert "1234 5678 9012" not in masked

        triage = TriageResult(
            task_type=TaskType.UNSUPPORTED,
            sentiment=Sentiment.ANGRY,
            urgency=Urgency.CRITICAL,
            wants_human=True,
        )

        escalate, reason = should_escalate(triage, 0.0, 0, 0)
        assert escalate is True

        ticket = create_ticket(
            user_id="student_c",
            masked_request=masked,
            reason=reason,
            triage=triage,
            has_pii=True,
        )
        assert "sk-secret" not in ticket.handoff_note
        assert "1234 5678 9012" not in ticket.handoff_note


class TestMeter:
    """Meter callback tracks calls correctly."""

    def test_meter_summary_structure(self):
        from app.metering import Meter
        meter = Meter()
        s = meter.summary()
        assert "by_model" in s
        assert "total" in s
        assert s["total"]["calls"] == 0


class TestSandboxEnvironment:
    """The sandbox strips the parent environment (no API keys leak in), but Windows still needs
    SYSTEMROOT & co. or pytest's asyncio-based plugins crash with WinError 10106."""

    def test_no_secrets_inherited(self, monkeypatch):
        from app.execution.sandbox import _sandbox_env
        monkeypatch.setenv("GROQ_API_KEY", "sk-should-not-leak")
        env = _sandbox_env("/tmp/x")
        assert "GROQ_API_KEY" not in env
        assert env["HOME"] == "/tmp/x"

    def test_windows_keeps_systemroot(self, monkeypatch):
        from app.execution import sandbox
        monkeypatch.setattr(sandbox.os, "name", "nt")
        monkeypatch.setenv("SYSTEMROOT", r"C:\Windows")
        monkeypatch.setenv("TEMP", r"C:\Temp")
        env = sandbox._sandbox_env(r"C:\sandbox")
        assert env["SYSTEMROOT"] == r"C:\Windows"
        assert env["TEMP"] == r"C:\Temp"
        assert env["USERPROFILE"] == r"C:\sandbox"

    def test_posix_env_unchanged(self, monkeypatch):
        from app.execution import sandbox
        monkeypatch.setattr(sandbox.os, "name", "posix")
        monkeypatch.setenv("SYSTEMROOT", r"C:\Windows")
        assert set(sandbox._sandbox_env("/tmp/x")) == {"PATH", "HOME", "PYTHONPATH", "LANG"}
