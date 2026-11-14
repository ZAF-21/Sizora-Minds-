"""
LangGraph typed state for the CodeForge orchestrator.
"""

from __future__ import annotations
from typing import Annotated, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

from app.models import (
    RoutingResult, Requirements, GeneratedCode, GeneratedTests,
    PolicyResult, TriageResult, EscalationTicket, ExecutionReport,
    AgentMetrics,
)


def _merge_metrics(old: list[AgentMetrics], new: list[AgentMetrics]) -> list[AgentMetrics]:
    return old + new


class CodeForgeState(TypedDict, total=False):
    # Input
    user_id: str
    user_role: str
    raw_request: str
    masked_request: str

    # Triage (R3)
    triage: TriageResult

    # Level 1 pipeline
    routing: RoutingResult
    requirements: Requirements
    generated_code: GeneratedCode
    generated_tests: GeneratedTests

    # Execution (R2)
    policy_result: PolicyResult
    execution_report: ExecutionReport
    idempotency_key: str

    # Escalation (R3)
    escalation_ticket: Optional[EscalationTicket]
    should_escalate: bool
    escalation_reason: str

    # Session tracking
    policy_denial_count: int
    failed_repair_count: int
    frustration_score: float
    turn_count: int

    # Metering (R4)
    metrics: Annotated[list[AgentMetrics], _merge_metrics]

    # Control flow
    error: str
    tier: str  # "primary", "fallback", "template", "degraded"
