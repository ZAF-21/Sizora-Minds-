"""
R6: Golden set evaluation gate — runs golden_set.json with hard rules at 100%.
Hard cases use plain Python (no LLM calls). Soft cases may require LLM.
"""

import json
import pytest
from pathlib import Path

from app.security.privacy import mask_pii, has_pii
from app.execution.policy import evaluate_code_policy
from app.execution.idempotency import IdempotencyStore
from app.config import get_user_config
from app.security.identity import validate_role_from_config
from app.resilience.templates import match_template
from app.models import PolicyVerdict

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.json"


@pytest.fixture(scope="module")
def golden_set():
    with open(GOLDEN_SET_PATH) as f:
        data = json.load(f)
    return data["cases"]


@pytest.fixture(scope="module")
def hard_cases(golden_set):
    return [c for c in golden_set if c["type"] == "hard"]


@pytest.fixture(scope="module")
def soft_cases(golden_set):
    return [c for c in golden_set if c["type"] == "soft"]


# ═══════════════════════════════════════════════════════════════════════════
# HARD CASES — must pass 100%
# ═══════════════════════════════════════════════════════════════════════════

class TestHardCases:
    def test_h01_identity_from_config(self, hard_cases):
        """Role comes from config, not from message."""
        case = next(c for c in hard_cases if c["id"] == "H01")
        role = validate_role_from_config(case["user_id"])
        assert role == case["expected_role"]

    def test_h02_api_key_masked(self, hard_cases):
        case = next(c for c in hard_cases if c["id"] == "H02")
        masked = mask_pii(case["input"])
        assert case["mask_token"] in masked
        assert "sk-1234" not in masked

    def test_h03_email_masked(self, hard_cases):
        case = next(c for c in hard_cases if c["id"] == "H03")
        masked = mask_pii(case["input"])
        assert case["mask_token"] in masked

    def test_h04_aadhaar_masked(self, hard_cases):
        case = next(c for c in hard_cases if c["id"] == "H04")
        masked = mask_pii(case["input"])
        assert case["mask_token"] in masked

    def test_h05_phone_masked(self, hard_cases):
        case = next(c for c in hard_cases if c["id"] == "H05")
        masked = mask_pii(case["input"])
        assert case["mask_token"] in masked

    def test_h06_normal_number_not_masked(self, hard_cases):
        case = next(c for c in hard_cases if c["id"] == "H06")
        masked = mask_pii(case["input"])
        assert masked == case["input"]  # Nothing should be masked

    def test_h07_destructive_code_denied(self, hard_cases):
        """Policy gate must deny code that deletes files."""
        code = "import os\nimport shutil\nshutil.rmtree(os.path.expanduser('~'))"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY

    def test_h08_exec_denied(self, hard_cases):
        code = "exec('import os; os.system(\"rm -rf /\")')"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY

    def test_h09_idempotency_key_stable(self, hard_cases):
        key1 = IdempotencyStore.make_key("student_a", "def is_palindrome(s): pass", "def test(): pass")
        key2 = IdempotencyStore.make_key("student_a", "def is_palindrome(s): pass", "def test(): pass")
        assert key1 == key2

    def test_h10_safe_code_allowed(self, hard_cases):
        code = "def add(a: int, b: int) -> int:\n    return a + b"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.ALLOW


# ═══════════════════════════════════════════════════════════════════════════
# SOFT CASES — at least 85% must pass (tests here, threshold in CI)
# ═══════════════════════════════════════════════════════════════════════════

class TestSoftCases:
    def test_s11_ticket_no_pii(self, soft_cases):
        """Ticket must contain masked text, not raw PII."""
        from app.escalation.ticket import create_ticket
        from app.models import TriageResult, TaskType, Sentiment, Urgency

        case = next(c for c in soft_cases if c["id"] == "S11")
        masked = mask_pii(case["input"])
        assert "sk-" not in masked

        triage = TriageResult(
            task_type=TaskType.UNSUPPORTED,
            sentiment=Sentiment.ANGRY,
            urgency=Urgency.CRITICAL,
            wants_human=True,
        )
        ticket = create_ticket(
            user_id="student_c",
            masked_request=masked,
            reason="Angry + wants human + PII",
            triage=triage,
            has_pii=True,
        )
        assert "sk-" not in ticket.handoff_note
        assert "1234 5678 9012" not in ticket.handoff_note

    def test_s12_template_fallback_palindrome(self, soft_cases):
        case = next(c for c in soft_cases if c["id"] == "S12")
        template = match_template(case["input"])
        assert template is not None
        assert "palindrome" in template.code.lower() or "is_palindrome" in template.code
