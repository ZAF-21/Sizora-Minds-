"""
CodeForge Streamlit chat interface.
Run: streamlit run streamlit_app.py
"""

from __future__ import annotations
import streamlit as st
from app.config import get_user_config, USERS
from app.security.privacy import mask_pii, has_pii
from app.execution.policy import evaluate_code_policy
from app.execution.sandbox import run_in_sandbox
from app.execution.idempotency import IdempotencyStore, IDEMPOTENCY_STORE
from app.execution.report import build_report
from app.escalation.rules import should_escalate, compute_frustration_score
from app.escalation.ticket import create_ticket
from app.resilience.templates import match_template
from app.resilience.chaos import enable_chaos, disable_chaos, is_chaos_enabled
from app.models import (
    PolicyVerdict, ExecutionReport, TriageResult, TaskType,
    Sentiment, Urgency,
)

st.set_page_config(page_title="CodeForge", page_icon="anvil", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "frustration_score" not in st.session_state:
    st.session_state.frustration_score = 0.0
if "policy_denial_count" not in st.session_state:
    st.session_state.policy_denial_count = 0
if "failed_repair_count" not in st.session_state:
    st.session_state.failed_repair_count = 0


def process_request(message: str, user_id: str, chaos_mode: bool) -> str:
    output_parts = []

    if chaos_mode and not is_chaos_enabled():
        enable_chaos(0.6)
    elif not chaos_mode and is_chaos_enabled():
        disable_chaos()

    try:
        user = get_user_config(user_id)
    except PermissionError as e:
        return f"Error: {e}"

    output_parts.append(f"**User:** `{user.user_id}` | **Role:** `{user.role}`")

    masked = mask_pii(message)
    if masked != message:
        output_parts.append(f"**PII Detected & Masked:**\n> {masked}")
    else:
        output_parts.append(f"**Request:** {masked}")

    wants_human = any(kw in message.lower() for kw in ["get me a human", "talk to a person", "escalate", "support"])
    is_angry = any(kw in message.upper() for kw in ["NOT WORKING", "!!!", "TERRIBLE", "AWFUL", "HATE"])
    is_frustrated = any(kw in message.lower() for kw in ["frustrated", "annoyed", "disappointing", "unhappy"])

    if is_angry:
        sentiment = Sentiment.ANGRY
    elif is_frustrated:
        sentiment = Sentiment.FRUSTRATED
    else:
        sentiment = Sentiment.CALM

    triage = TriageResult(
        task_type=TaskType.PYTHON_FUNCTION,
        sentiment=sentiment,
        urgency=Urgency.HIGH if is_angry else Urgency.LOW,
        wants_human=wants_human,
    )

    st.session_state.frustration_score = compute_frustration_score(
        st.session_state.frustration_score, triage
    )

    escalate, reason = should_escalate(
        triage,
        st.session_state.frustration_score,
        st.session_state.policy_denial_count,
        st.session_state.failed_repair_count,
    )

    if escalate:
        pii_present = has_pii(message)
        ticket = create_ticket(
            user_id=user_id,
            masked_request=masked,
            reason=reason,
            triage=triage,
            has_pii=pii_present,
        )
        output_parts.append(f"\n---\n### ESCALATED\n**Reason:** {reason}")
        output_parts.append(f"**Ticket:** `{ticket.ticket_id}` | **Priority:** `{ticket.priority.value}` | **SLA:** {ticket.sla_minutes} min")
        output_parts.append(f"**Handoff Note:**\n```\n{ticket.handoff_note}\n```")
        return "\n".join(output_parts)

    template = match_template(masked)

    if template:
        code = template.code
        tests = template.tests
        tier = "TEMPLATE"
        output_parts.append(f"**Served by:** `{tier}` tier (deterministic, no model call)")
    else:
        try:
            from app.agents.router import route_request
            from app.agents.requirements import extract_requirements
            from app.agents.code_generator import generate_code
            from app.agents.test_generator import generate_tests

            routing = route_request(masked)
            output_parts.append(f"**Routing:** `{routing.task_type.value}`")

            reqs = extract_requirements(masked)
            output_parts.append(f"**Function:** `{reqs.function_name}`")

            gen_code = generate_code(reqs)
            code = gen_code.code
            gen_tests = generate_tests(code, reqs)
            tests = gen_tests.test_code
            tier = "PRIMARY"
            output_parts.append(f"**Served by:** `{tier}` tier (LLM-generated)")
        except Exception as e:
            output_parts.append(f"\n---\n**All tiers failed:** {str(e)[:100]}")
            output_parts.append("A support ticket has been created.")
            return "\n".join(output_parts)

    policy = evaluate_code_policy(code)
    output_parts.append(f"**Policy:** `{policy.verdict.value}`")

    if policy.verdict == PolicyVerdict.DENY:
        st.session_state.policy_denial_count += 1
        output_parts.append(f"\n---\n### DENIED\n{'; '.join(policy.reasons)}\n\nNo code was executed.")
        return "\n".join(output_parts)

    if policy.verdict == PolicyVerdict.NEEDS_APPROVAL:
        output_parts.append(f"**Needs Approval** — {'; '.join(policy.reasons)}")
        output_parts.append("In production, this would pause for human review.")
        if tier in ("TEMPLATE", "DEGRADED"):
            output_parts.append("**Degraded tier never auto-approves risky code.**")
            return "\n".join(output_parts)

    idem_key = IdempotencyStore.make_key(user_id, code, tests)
    cached = IDEMPOTENCY_STORE.get(idem_key)
    if cached:
        output_parts.append(f"\n---\n**Idempotency hit** — returning cached result")
        output_parts.append(f"```\n{build_report(cached)}\n```")
        return "\n".join(output_parts)

    result = run_in_sandbox(code, tests)

    report = ExecutionReport(
        request_summary=masked[:100],
        code=code,
        tests=tests,
        policy_verdict=policy.verdict,
        tests_passed=result["passed"],
        test_output=result["output"] + result.get("error", ""),
        exit_code=result["exit_code"],
        idempotency_key=idem_key,
        tier=tier.lower(),
    )
    IDEMPOTENCY_STORE.store(idem_key, report)

    output_parts.append(f"\n---\n```\n{build_report(report)}\n```")
    return "\n".join(output_parts)


# ── UI Layout ────────────────────────────────────────────────────────────────

st.title("CodeForge")
st.caption("Production-Grade NL-to-Code Agent — Turn plain English into working, tested Python code.")

with st.sidebar:
    st.header("Configuration")
    user_id = st.selectbox("User (from config, not message)", list(USERS.keys()), index=0)
    chaos_mode = st.toggle("Chaos Mode (60% model failure)", value=False)

    st.divider()
    st.subheader("Try these scenarios")
    st.markdown("""
    - **Normal:** `Write a function that checks if a string is a palindrome`
    - **Destructive:** `Write a function that deletes every file in my home folder, and run it`
    - **PII + Angry:** `sk-abc123456789012345678901 THIS IS NOT WORKING!!! get me a human`
    - **Idempotency:** Submit the same request twice
    - **Chaos mode:** Toggle chaos and try template requests
    """)

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.frustration_score = 0.0
        st.session_state.policy_denial_count = 0
        st.session_state.failed_repair_count = 0
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("e.g., Write a Python function that checks if a string is a palindrome"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            response = process_request(prompt, user_id, chaos_mode)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
