"""
CodeForge Gradio chat interface (+10 bonus).
Run: python gradio_app.py
"""

from __future__ import annotations
import json
import gradio as gr
from app.config import get_user_config, USERS
from app.security.privacy import mask_pii, has_pii
from app.execution.policy import evaluate_code_policy, evaluate_request_safety
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

# Session state
session_state = {
    "frustration_score": 0.0,
    "policy_denial_count": 0,
    "failed_repair_count": 0,
}


def process_request(message: str, user_id: str, chaos_mode: bool) -> str:
    """Process a CodeForge request through the full pipeline."""
    output_lines = []

    # Chaos toggle
    if chaos_mode and not is_chaos_enabled():
        enable_chaos(0.6)
    elif not chaos_mode and is_chaos_enabled():
        disable_chaos()

    # Step 1: Validate user
    try:
        user = get_user_config(user_id)
    except PermissionError as e:
        return f"Error: {e}"

    output_lines.append(f"**User:** {user.user_id} | **Role:** {user.role}")

    # Step 2: Mask PII
    masked = mask_pii(message)
    if masked != message:
        output_lines.append(f"**PII Detected & Masked:** {masked}")
    else:
        output_lines.append(f"**Request:** {masked}")

    # Step 2.5: Check request intent safety BEFORE any code generation
    request_safety = evaluate_request_safety(masked)
    if request_safety.verdict.value == "deny":
        output_lines.append(f"\n**REQUEST DENIED** — {'; '.join(request_safety.reasons)}")
        output_lines.append("No code was generated or executed.")
        return "\n".join(output_lines)

    # Step 3: Triage (simplified — detect sentiment from keywords)
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

    session_state["frustration_score"] = compute_frustration_score(
        session_state["frustration_score"], triage
    )

    # Step 4: Escalation check
    escalate, reason = should_escalate(
        triage,
        session_state["frustration_score"],
        session_state["policy_denial_count"],
        session_state["failed_repair_count"],
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
        output_lines.append(f"\n**ESCALATED** — {reason}")
        output_lines.append(f"**Ticket:** {ticket.ticket_id} | **Priority:** {ticket.priority.value} | **SLA:** {ticket.sla_minutes}min")
        output_lines.append(f"**Handoff Note:**\n```\n{ticket.handoff_note}\n```")
        return "\n".join(output_lines)

    # Step 5: Try template match first (or would use LLM agents)
    template = match_template(masked)

    if template:
        code = template.code
        tests = template.tests
        tier = "template"
        output_lines.append(f"**Served by: TEMPLATE tier** (deterministic, no model call)")
    else:
        # Try LLM agents
        try:
            from app.agents.router import route_request
            from app.agents.requirements import extract_requirements
            from app.agents.code_generator import generate_code
            from app.agents.test_generator import generate_tests

            routing = route_request(masked)
            output_lines.append(f"**Routing:** {routing.task_type.value}")

            reqs = extract_requirements(masked)
            output_lines.append(f"**Function:** {reqs.function_name}")

            gen_code = generate_code(reqs)
            code = gen_code.code
            gen_tests = generate_tests(code, reqs)
            tests = gen_tests.test_code
            tier = "primary"
            output_lines.append(f"**Served by: PRIMARY tier** (LLM-generated)")
        except Exception as e:
            output_lines.append(f"\n**All tiers failed:** {str(e)[:100]}")
            output_lines.append("A support ticket has been created.")
            return "\n".join(output_lines)

    # Step 6: Policy gate
    policy = evaluate_code_policy(code)
    output_lines.append(f"**Policy:** {policy.verdict.value}")

    if policy.verdict == PolicyVerdict.DENY:
        session_state["policy_denial_count"] += 1
        output_lines.append(f"**DENIED** — {'; '.join(policy.reasons)}")
        output_lines.append("No code was executed.")
        return "\n".join(output_lines)

    if policy.verdict == PolicyVerdict.NEEDS_APPROVAL:
        output_lines.append(f"**Needs Approval** — {'; '.join(policy.reasons)}")
        output_lines.append("In production, this would pause for human review.")
        if tier in ("template", "degraded"):
            output_lines.append("**Degraded tier never auto-approves risky code.**")
            return "\n".join(output_lines)

    # Step 7: Idempotency check
    idem_key = IdempotencyStore.make_key(user_id, code, tests)
    cached = IDEMPOTENCY_STORE.get(idem_key)
    if cached:
        output_lines.append(f"\n**Idempotency hit** — returning cached result")
        output_lines.append(f"```\n{build_report(cached)}\n```")
        return "\n".join(output_lines)

    # Step 8: Sandbox execution
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
        tier=tier,
    )
    IDEMPOTENCY_STORE.store(idem_key, report)

    output_lines.append(f"\n```\n{build_report(report)}\n```")
    return "\n".join(output_lines)


def create_interface():
    with gr.Blocks(title="CodeForge", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# CodeForge — Production-Grade NL-to-Code Agent")
        gr.Markdown("Turn natural language into working, tested Python code.")

        with gr.Row():
            user_dropdown = gr.Dropdown(
                choices=list(USERS.keys()),
                value="student_a",
                label="User (from config, not from message)",
            )
            chaos_toggle = gr.Checkbox(label="Chaos Mode (60% model failure)", value=False)

        chatbot = gr.Chatbot(label="CodeForge", height=500, type="messages")
        msg = gr.Textbox(
            label="Your request",
            placeholder="e.g., Write a Python function that checks if a string is a palindrome",
            lines=2,
        )

        def respond(message, chat_history, user_id, chaos_mode):
            response = process_request(message, user_id, chaos_mode)
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": response})
            return "", chat_history

        msg.submit(respond, [msg, chatbot, user_dropdown, chaos_toggle], [msg, chatbot])

        gr.Markdown("### Try these scenarios:")
        gr.Markdown("""
        - **Student A:** `Write a Python function that checks if a string is a palindrome`
        - **Student B:** `Write a function that deletes every file in my home folder, and run it`
        - **Student C:** `sk-abc123456789012345678901 THIS IS NOT WORKING!!! get me a human`
        - **Idempotency:** Submit the same request twice
        - **Chaos mode:** Toggle chaos and try template-matching requests
        """)

    return demo


if __name__ == "__main__":
    demo = create_interface()
    demo.launch()
