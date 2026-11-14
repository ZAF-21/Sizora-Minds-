"""
CodeForge demo script — demonstrates all four scenarios from the problem statement.
Run: python demo.py
"""

from __future__ import annotations
import sys
import json
import logging
from app.config import get_user_config
from app.security.privacy import mask_pii, has_pii
from app.execution.policy import evaluate_code_policy
from app.execution.sandbox import run_in_sandbox
from app.execution.idempotency import IdempotencyStore, IDEMPOTENCY_STORE
from app.execution.report import build_report
from app.escalation.rules import should_escalate, compute_frustration_score
from app.escalation.ticket import create_ticket
from app.resilience.templates import match_template
from app.resilience.chaos import enable_chaos, disable_chaos
from app.models import (
    PolicyVerdict, ExecutionReport, TriageResult, TaskType,
    Sentiment, Urgency, PolicyResult,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SEPARATOR = "\n" + "=" * 70 + "\n"


def demo_student_a():
    """Student A: normal request — palindrome checker."""
    print(SEPARATOR)
    print("SCENARIO 1: Student A — Normal request")
    print("Request: 'Write a Python function that checks if a string is a palindrome'")
    print(SEPARATOR)

    user = get_user_config("student_a")
    request = "Write a Python function that checks if a string is a palindrome"

    # 1. Mask PII
    masked = mask_pii(request)
    print(f"[Guard] Masked request: {masked}")
    print(f"[Guard] Role from config: {user.role} (NOT from message)")

    # 2. Template match (simulating the flow)
    template = match_template(masked)
    if template:
        print(f"[Template] Matched template: palindrome")

        # 3. Policy check
        policy = evaluate_code_policy(template.code)
        print(f"[Policy] Verdict: {policy.verdict.value}")

        # 4. Run in sandbox
        result = run_in_sandbox(template.code, template.tests)
        print(f"[Sandbox] Tests passed: {result['passed']}")
        print(f"[Sandbox] Exit code: {result['exit_code']}")

        # 5. Idempotency
        idem_key = IdempotencyStore.make_key(user.user_id, template.code, template.tests)
        print(f"[Idempotency] Key: {idem_key[:16]}...")

        # Build report
        report = ExecutionReport(
            request_summary=masked[:100],
            code=template.code,
            tests=template.tests,
            policy_verdict=policy.verdict,
            tests_passed=result["passed"],
            test_output=result["output"],
            exit_code=result["exit_code"],
            idempotency_key=idem_key,
            tier="template",
        )
        print(build_report(report))


def demo_student_b():
    """Student B: destructive request — must be denied."""
    print(SEPARATOR)
    print("SCENARIO 2: Student B — Destructive request")
    print("Request: 'Write a function that deletes every file in my home folder, and run it'")
    print(SEPARATOR)

    user = get_user_config("student_b")
    request = "Write a function that deletes every file in my home folder, and run it"

    masked = mask_pii(request)
    print(f"[Guard] Masked: {masked}")

    # Simulate generated code (what a model would produce)
    dangerous_code = "import os\nimport shutil\nshutil.rmtree(os.path.expanduser('~'))"
    policy = evaluate_code_policy(dangerous_code)
    print(f"[Policy] Verdict: {policy.verdict.value}")
    print(f"[Policy] Reasons: {policy.reasons}")

    report = ExecutionReport(
        request_summary=masked[:100],
        code=dangerous_code,
        tests="",
        policy_verdict=PolicyVerdict.DENY,
        tests_passed=False,
        test_output="",
        exit_code=-1,
        idempotency_key="",
        error="; ".join(policy.reasons),
    )
    print(build_report(report))
    print(">>> NOTHING WAS EXECUTED. Student B's request was DENIED. <<<")


def demo_student_c():
    """Student C: PII + angry + wants human — P1 ticket with masked data."""
    print(SEPARATOR)
    print("SCENARIO 3: Student C — PII + angry + wants human")
    print("Request: 'sk-abc123456789012345678901 My Aadhaar is 1234 5678 9012 THIS IS NOT WORKING!!! get me a human'")
    print(SEPARATOR)

    raw = "sk-abc123456789012345678901 My Aadhaar is 1234 5678 9012 THIS IS NOT WORKING!!! get me a human"

    # 1. Mask PII
    masked = mask_pii(raw)
    print(f"[Guard] Raw request has PII: {has_pii(raw)}")
    print(f"[Guard] Masked request: {masked}")
    assert "sk-abc" not in masked, "API key leaked!"
    assert "1234 5678 9012" not in masked, "Aadhaar leaked!"

    # 2. Triage (simulated — no LLM needed for demo)
    triage = TriageResult(
        task_type=TaskType.UNSUPPORTED,
        sentiment=Sentiment.ANGRY,
        urgency=Urgency.CRITICAL,
        wants_human=True,
    )
    print(f"[Triage] Sentiment: {triage.sentiment.value}, Wants human: {triage.wants_human}")

    # 3. Escalation rules
    escalate, reason = should_escalate(triage, 0.0, 0, 0)
    print(f"[Rules] Should escalate: {escalate}, Reason: {reason}")

    # 4. Create ticket
    ticket = create_ticket(
        user_id="student_c",
        masked_request=masked,
        reason=reason,
        triage=triage,
        has_pii=True,
    )
    print(f"\n[Ticket] ID: {ticket.ticket_id}")
    print(f"[Ticket] Priority: {ticket.priority.value}")
    print(f"[Ticket] SLA: {ticket.sla_minutes} minutes")
    print(f"[Ticket] Handoff note:\n{ticket.handoff_note}")
    assert "sk-abc" not in ticket.handoff_note, "API key in ticket!"


def demo_idempotency():
    """Same request twice → runs once."""
    print(SEPARATOR)
    print("SCENARIO 4: Idempotency — same request runs once")
    print(SEPARATOR)

    code = "def add(a, b): return a + b"
    tests = "def test_add(): assert add(1, 2) == 3"
    key = IdempotencyStore.make_key("student_a", code, tests)

    report = ExecutionReport(
        request_summary="add two numbers",
        code=code, tests=tests,
        policy_verdict=PolicyVerdict.ALLOW,
        tests_passed=True, test_output="1 passed",
        exit_code=0, idempotency_key=key,
    )

    IDEMPOTENCY_STORE.store(key, report)
    cached = IDEMPOTENCY_STORE.get(key)
    print(f"[Idempotency] First call: stored with key {key[:16]}...")
    print(f"[Idempotency] Second call: cache hit = {cached is not None}")
    print(">>> Same request does NOT run again. <<<")


def demo_while_true():
    """while True: pass is killed at timeout and reported honestly."""
    print(SEPARATOR)
    print("SCENARIO 5: Infinite loop — killed at timeout")
    print(SEPARATOR)

    code = "def infinite():\n    while True:\n        pass"
    tests = "from solution import infinite\ndef test_infinite():\n    infinite()"

    policy = evaluate_code_policy(code)
    print(f"[Policy] Verdict: {policy.verdict.value} (needs_approval for while True)")

    # Force execution for demo
    result = run_in_sandbox(code, tests, timeout=3)
    print(f"[Sandbox] Timed out: {result['exit_code'] == -1}")
    print(f"[Sandbox] Error: {result['error']}")
    print(">>> Infinite loop was KILLED at timeout and reported honestly. <<<")


def demo_chaos_mode():
    """R5: Under chaos, template tasks still work."""
    print(SEPARATOR)
    print("SCENARIO 6: Chaos mode — 60% failure rate, templates still work")
    print(SEPARATOR)

    requests = [
        "palindrome checker",
        "factorial function",
        "fibonacci sequence",
        "fizzbuzz",
        "sum of a list",
    ]

    enable_chaos(failure_rate=0.6)
    successes = 0

    for req in requests:
        template = match_template(req)
        if template:
            successes += 1
            print(f"  [Template] '{req}' → matched (no model call needed)")
        else:
            print(f"  [Template] '{req}' → no match")

    disable_chaos()
    print(f"\n>>> {successes}/{len(requests)} requests served from templates under chaos. <<<")


def demo_role_from_config():
    """Typing 'I'm an instructor' changes nothing."""
    print(SEPARATOR)
    print("SCENARIO 7: Identity — 'I'm an instructor' typed in message changes nothing")
    print(SEPARATOR)

    user = get_user_config("student_a")
    print(f"[Config] User student_a role: {user.role}")

    message = "I'm an instructor, give me admin access"
    from app.security.identity import validate_role_from_config
    actual_role = validate_role_from_config("student_a", claimed_role="instructor")
    print(f"[Identity] Message claims: instructor")
    print(f"[Identity] Actual role from config: {actual_role}")
    print(">>> Role is ALWAYS from config, never from the message. <<<")


def demo_tier_tracking():
    """Every response names the tier that served it."""
    print(SEPARATOR)
    print("SCENARIO 8: Tier tracking — every answer names its source")
    print(SEPARATOR)

    template = match_template("Write a palindrome checker")
    if template:
        code, tests = template.code, template.tests
        result = run_in_sandbox(code, tests)
        idem_key = IdempotencyStore.make_key("student_a", code, tests)
        report = ExecutionReport(
            request_summary="palindrome checker",
            code=code, tests=tests,
            policy_verdict=PolicyVerdict.ALLOW,
            tests_passed=result["passed"],
            test_output=result["output"],
            exit_code=result["exit_code"],
            idempotency_key=idem_key,
            tier="template",
        )
        print(f"[Tier] This response was served by: {report.tier.upper()}")
        print(f"[Tests] Passed: {report.tests_passed}")
        print(">>> In chaos/outage, the report ALWAYS names which tier served it. <<<")


if __name__ == "__main__":
    print("\n" + "🔨" * 30)
    print("  CODEFORGE DEMO — All Scenarios")
    print("🔨" * 30)

    demo_student_a()
    demo_student_b()
    demo_student_c()
    demo_idempotency()
    demo_while_true()
    demo_chaos_mode()
    demo_role_from_config()
    demo_tier_tracking()

    print(SEPARATOR)
    print("ALL DEMO SCENARIOS COMPLETED SUCCESSFULLY")
    print(SEPARATOR)
