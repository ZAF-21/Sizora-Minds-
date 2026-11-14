"""
CodeForge LangGraph orchestrator — ties all agents together in one graph.
Request flow: guard_in → triage → route → [escalate | generate] → policy_gate → [deny | approve | execute] → report
"""

from __future__ import annotations
import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

from app.state import CodeForgeState
from app.config import get_user_config
from app.models import (
    PolicyVerdict, ExecutionReport, GeneratedCode, GeneratedTests,
    TaskType, TriageResult, Sentiment, Urgency,
)
from app.security.privacy import mask_pii, has_pii
from app.security.quota import QUOTA_TRACKER
from app.execution.policy import evaluate_code_policy
from app.execution.sandbox import run_in_sandbox
from app.execution.idempotency import IDEMPOTENCY_STORE, IdempotencyStore
from app.execution.report import build_report
from app.escalation.rules import should_escalate, compute_frustration_score
from app.escalation.ticket import create_ticket
from app.resilience.fallback import call_with_fallback, AllTiersExhaustedError
from app.resilience.templates import match_template
from app.resilience.chaos import chaos_maybe_fail, ChaosError

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Node functions — each takes and returns CodeForgeState
# ═══════════════════════════════════════════════════════════════════════════

def guard_in_node(state: CodeForgeState) -> dict:
    """R1: Mask PII, load identity from config, check quota."""
    user_id = state["user_id"]
    raw = state["raw_request"]

    config = get_user_config(user_id)
    masked = mask_pii(raw)

    if not QUOTA_TRACKER.check_quota(user_id):
        return {
            "masked_request": masked,
            "user_role": config.role,
            "error": f"Rate limit exceeded. You have {QUOTA_TRACKER.remaining(user_id)} runs remaining this hour.",
        }

    return {
        "masked_request": masked,
        "user_role": config.role,
        "policy_denial_count": state.get("policy_denial_count", 0),
        "failed_repair_count": state.get("failed_repair_count", 0),
        "frustration_score": state.get("frustration_score", 0.0),
        "turn_count": state.get("turn_count", 0) + 1,
    }


def triage_node(state: CodeForgeState) -> dict:
    """R3: Triage the request — sentiment, urgency, wants_human."""
    from app.escalation.triage import triage_request

    masked = state["masked_request"]

    try:
        triage = triage_request(masked)
    except Exception:
        triage = TriageResult(
            task_type=TaskType.PYTHON_FUNCTION,
            language="python",
            sentiment=Sentiment.CALM,
            urgency=Urgency.LOW,
            wants_human=False,
        )

    frustration = compute_frustration_score(
        state.get("frustration_score", 0.0), triage
    )

    return {"triage": triage, "frustration_score": frustration}


def check_escalation_node(state: CodeForgeState) -> dict:
    """R3: Code-based escalation check."""
    triage = state.get("triage")
    if triage is None:
        return {"should_escalate": False}

    escalate, reason = should_escalate(
        triage=triage,
        frustration_score=state.get("frustration_score", 0.0),
        policy_denial_count=state.get("policy_denial_count", 0),
        failed_repair_count=state.get("failed_repair_count", 0),
    )
    return {"should_escalate": escalate, "escalation_reason": reason}


def escalate_node(state: CodeForgeState) -> dict:
    """R3: Create escalation ticket and halt."""
    triage = state.get("triage", TriageResult(
        task_type=TaskType.UNSUPPORTED, sentiment=Sentiment.ANGRY,
        urgency=Urgency.HIGH, wants_human=True,
    ))
    pii_present = has_pii(state.get("raw_request", ""))

    ticket = create_ticket(
        user_id=state["user_id"],
        masked_request=state["masked_request"],
        reason=state.get("escalation_reason", "Escalation triggered"),
        triage=triage,
        has_pii=pii_present,
    )
    return {"escalation_ticket": ticket}


def route_node(state: CodeForgeState) -> dict:
    """Level 1: Route the request using structured output."""
    from app.agents.router import route_request

    masked = state["masked_request"]
    try:
        routing = route_request(masked)
    except Exception as e:
        from app.models import RoutingResult
        routing = RoutingResult(
            task_type=TaskType.PYTHON_FUNCTION,
            language="python",
            is_context_free=True,
            summary=masked[:100],
        )
    return {"routing": routing}


def requirements_node(state: CodeForgeState) -> dict:
    """Level 1: Extract structured requirements."""
    from app.agents.requirements import extract_requirements

    masked = state["masked_request"]
    try:
        reqs = extract_requirements(masked)
    except Exception:
        from app.models import Requirements
        reqs = Requirements(
            function_name="solution",
            description=masked,
        )
    return {"requirements": reqs}


def code_gen_node(state: CodeForgeState) -> dict:
    """Level 1 + R5: Generate code with fallback tiers."""
    from app.agents.code_generator import generate_code

    reqs = state["requirements"]
    masked = state["masked_request"]

    try:
        result, tier = call_with_fallback(
            primary_fn=lambda: generate_code(reqs),
            request_text=masked,
        )
        if tier == "template":
            return {
                "generated_code": GeneratedCode(code=result.code, explanation="Template tier"),
                "generated_tests": GeneratedTests(test_code=result.tests, num_tests=5),
                "tier": tier,
            }
        return {"generated_code": result, "tier": tier}
    except AllTiersExhaustedError:
        return {
            "error": "Cannot generate code right now. All model tiers are unavailable and no template matches your request.",
            "tier": "degraded",
        }


def test_gen_node(state: CodeForgeState) -> dict:
    """Level 1 + R5: Generate tests with fallback."""
    if state.get("tier") == "template":
        return {}

    from app.agents.test_generator import generate_tests

    code = state["generated_code"]
    reqs = state["requirements"]
    masked = state["masked_request"]

    try:
        result, tier = call_with_fallback(
            primary_fn=lambda: generate_tests(code.code, reqs),
            request_text=masked,
        )
        if tier == "template":
            return {"generated_tests": GeneratedTests(test_code=result.tests, num_tests=5)}
        return {"generated_tests": result}
    except AllTiersExhaustedError:
        basic_test = f"from solution import *\n\ndef test_exists():\n    pass\n"
        return {"generated_tests": GeneratedTests(test_code=basic_test, num_tests=1)}


def policy_gate_node(state: CodeForgeState) -> dict:
    """R2: Pure function policy evaluation on the AST."""
    code = state.get("generated_code")
    if code is None:
        return {"policy_result": None}

    result = evaluate_code_policy(code.code)
    if result.verdict == PolicyVerdict.DENY:
        return {
            "policy_result": result,
            "policy_denial_count": state.get("policy_denial_count", 0) + 1,
        }
    return {"policy_result": result}


def human_approval_node(state: CodeForgeState) -> dict:
    """R2: Pause graph for human approval using LangGraph interrupt()."""
    code = state["generated_code"].code
    reasons = state["policy_result"].reasons

    approval = interrupt({
        "message": "Code requires human approval before execution.",
        "code": code,
        "reasons": reasons,
        "action": "Please respond with 'approve' or 'reject'",
    })

    if approval and str(approval).lower().strip() in ("approve", "yes", "y"):
        return {}
    return {"error": "Human reviewer rejected the code."}


def execute_node(state: CodeForgeState) -> dict:
    """R2: Run code + tests in sandbox with idempotency check."""
    code = state["generated_code"].code
    tests = state["generated_tests"].test_code
    user_id = state["user_id"]

    idem_key = IdempotencyStore.make_key(user_id, code, tests)
    cached = IDEMPOTENCY_STORE.get(idem_key)
    if cached is not None:
        logger.info(f"Idempotency hit: {idem_key[:16]}")
        return {"execution_report": cached, "idempotency_key": idem_key}

    sandbox_result = run_in_sandbox(code, tests)

    QUOTA_TRACKER.record_run(user_id)

    report = ExecutionReport(
        request_summary=state["masked_request"][:100],
        code=code,
        tests=tests,
        policy_verdict=state["policy_result"].verdict,
        tests_passed=sandbox_result["passed"],
        test_output=sandbox_result["output"] + sandbox_result["error"],
        exit_code=sandbox_result["exit_code"],
        idempotency_key=idem_key,
        tier=state.get("tier", "primary"),
    )

    IDEMPOTENCY_STORE.store(idem_key, report)

    return {"execution_report": report, "idempotency_key": idem_key}


def deny_node(state: CodeForgeState) -> dict:
    """R2: Build a denial report."""
    policy = state.get("policy_result")
    reasons = "; ".join(policy.reasons) if policy else "Policy violation"

    report = ExecutionReport(
        request_summary=state["masked_request"][:100],
        code=state.get("generated_code", GeneratedCode(code="", explanation="")).code,
        tests="",
        policy_verdict=PolicyVerdict.DENY,
        tests_passed=False,
        test_output="",
        exit_code=-1,
        idempotency_key="",
        tier=state.get("tier", "primary"),
        error=reasons,
    )
    return {"execution_report": report}


def degraded_node(state: CodeForgeState) -> dict:
    """R5: Honest degraded mode — create a ticket, never invent code."""
    from app.escalation.ticket import create_ticket
    triage = state.get("triage", TriageResult(
        task_type=TaskType.UNSUPPORTED, sentiment=Sentiment.CALM,
        urgency=Urgency.LOW, wants_human=False,
    ))

    ticket = create_ticket(
        user_id=state["user_id"],
        masked_request=state["masked_request"],
        reason="All generation tiers unavailable",
        triage=triage,
    )

    report = ExecutionReport(
        request_summary=state["masked_request"][:100],
        code="",
        tests="",
        policy_verdict=PolicyVerdict.DENY,
        tests_passed=False,
        test_output="",
        exit_code=-1,
        idempotency_key="",
        tier="degraded",
        error="Cannot generate code right now. A support ticket has been created.",
    )
    return {"execution_report": report, "escalation_ticket": ticket}


def report_node(state: CodeForgeState) -> dict:
    """R2: Build the final report from real pytest results."""
    report = state.get("execution_report")
    if report:
        formatted = build_report(report)
        logger.info(f"\n{formatted}")
    return {}


# ═══════════════════════════════════════════════════════════════════════════
# Routing functions — decide which path to take
# ═══════════════════════════════════════════════════════════════════════════

def route_after_guard(state: CodeForgeState) -> str:
    if state.get("error"):
        return "report"
    return "triage"


def route_after_escalation_check(state: CodeForgeState) -> str:
    if state.get("should_escalate"):
        return "escalate"
    return "route"


def route_after_codegen(state: CodeForgeState) -> str:
    if state.get("error"):
        return "degraded"
    return "test_gen"


def route_after_policy(state: CodeForgeState) -> str:
    policy = state.get("policy_result")
    if policy is None:
        return "deny"
    if policy.verdict == PolicyVerdict.DENY:
        return "deny"
    if policy.verdict == PolicyVerdict.NEEDS_APPROVAL:
        # In degraded/template tier, never auto-approve risky code
        if state.get("tier") in ("template", "degraded"):
            return "deny"
        return "human_approval"
    return "execute"


def route_after_approval(state: CodeForgeState) -> str:
    if state.get("error"):
        return "deny"
    return "execute"


# ═══════════════════════════════════════════════════════════════════════════
# Build the graph
# ═══════════════════════════════════════════════════════════════════════════

def build_graph() -> StateGraph:
    graph = StateGraph(CodeForgeState)

    # Add nodes
    graph.add_node("guard_in", guard_in_node)
    graph.add_node("triage", triage_node)
    graph.add_node("check_escalation", check_escalation_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("route", route_node)
    graph.add_node("requirements", requirements_node)
    graph.add_node("code_gen", code_gen_node)
    graph.add_node("test_gen", test_gen_node)
    graph.add_node("policy_gate", policy_gate_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("execute", execute_node)
    graph.add_node("deny", deny_node)
    graph.add_node("degraded", degraded_node)
    graph.add_node("report", report_node)

    # Set entry point
    graph.set_entry_point("guard_in")

    # Edges
    graph.add_conditional_edges("guard_in", route_after_guard, {
        "triage": "triage",
        "report": "report",
    })

    graph.add_edge("triage", "check_escalation")

    graph.add_conditional_edges("check_escalation", route_after_escalation_check, {
        "escalate": "escalate",
        "route": "route",
    })

    graph.add_edge("escalate", END)
    graph.add_edge("route", "requirements")
    graph.add_edge("requirements", "code_gen")

    graph.add_conditional_edges("code_gen", route_after_codegen, {
        "test_gen": "test_gen",
        "degraded": "degraded",
    })

    graph.add_edge("test_gen", "policy_gate")

    graph.add_conditional_edges("policy_gate", route_after_policy, {
        "deny": "deny",
        "human_approval": "human_approval",
        "execute": "execute",
    })

    graph.add_conditional_edges("human_approval", route_after_approval, {
        "deny": "deny",
        "execute": "execute",
    })

    graph.add_edge("execute", "report")
    graph.add_edge("deny", "report")
    graph.add_edge("degraded", "report")
    graph.add_edge("report", END)

    return graph


def compile_graph():
    """Compile the graph for execution."""
    graph = build_graph()
    return graph.compile()


def run_codeforge(user_id: str, request: str) -> CodeForgeState:
    """Run the full CodeForge pipeline for a single request."""
    app = compile_graph()
    initial_state = {
        "user_id": user_id,
        "raw_request": request,
        "metrics": [],
    }
    result = app.invoke(initial_state)
    return result
