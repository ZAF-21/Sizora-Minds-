"""
Pydantic models for structured outputs across all agents.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ── Router / Parser Agent ────────────────────────────────────────────────────

class TaskType(str, Enum):
    PYTHON_FUNCTION = "python_function"
    SQL_QUERY = "sql_query"
    GENERAL_CODE = "general_code"
    UNSUPPORTED = "unsupported"

class RoutingResult(BaseModel):
    task_type: TaskType = Field(description="The type of code to generate")
    language: str = Field(default="python", description="Programming language")
    is_context_free: bool = Field(default=True, description="Whether this request can be cached")
    summary: str = Field(description="Brief summary of the request")


# ── Requirements Agent ───────────────────────────────────────────────────────

class Parameter(BaseModel):
    name: str
    type_hint: str = "Any"
    description: str = ""

class Requirements(BaseModel):
    function_name: str = Field(description="Name of the function to generate")
    parameters: list[Parameter] = Field(default_factory=list)
    return_type: str = Field(default="Any", description="Return type hint")
    description: str = Field(description="What the function should do")
    edge_cases: list[str] = Field(default_factory=list, description="Edge cases to handle")
    constraints: list[str] = Field(default_factory=list, description="Special constraints from the user")


# ── Code Generation Agent ────────────────────────────────────────────────────

class GeneratedCode(BaseModel):
    code: str = Field(description="The generated Python code")
    explanation: str = Field(default="", description="Brief explanation of the code")
    time_complexity: str = Field(default="", description="Big-O time complexity e.g. O(n)")
    space_complexity: str = Field(default="", description="Big-O space complexity e.g. O(1)")


# ── Test Generation Agent ────────────────────────────────────────────────────

class GeneratedTests(BaseModel):
    test_code: str = Field(description="pytest-style unit tests")
    num_tests: int = Field(default=0, description="Number of test cases")


# ── Triage / Escalation (R3) ────────────────────────────────────────────────

class Sentiment(str, Enum):
    CALM = "calm"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    DESPERATE = "desperate"

class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TriageResult(BaseModel):
    task_type: TaskType = Field(description="What kind of code is needed")
    language: str = Field(default="python")
    sentiment: Sentiment = Field(default=Sentiment.CALM)
    urgency: Urgency = Field(default=Urgency.LOW)
    wants_human: bool = Field(default=False, description="User explicitly asked for a person")


# ── Policy Gate (R2) ─────────────────────────────────────────────────────────

class PolicyVerdict(str, Enum):
    ALLOW = "allow"
    NEEDS_APPROVAL = "needs_approval"
    DENY = "deny"

class PolicyResult(BaseModel):
    verdict: PolicyVerdict
    reasons: list[str] = Field(default_factory=list)


# ── Escalation Ticket (R3) ──────────────────────────────────────────────────

class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class EscalationTicket(BaseModel):
    ticket_id: str
    user_id: str
    priority: Priority
    sla_minutes: int
    reason: str
    handoff_note: str = Field(description="Request, attempts, last failing test")
    created_at: str


# ── Execution Report (R2) ───────────────────────────────────────────────────

class ExecutionReport(BaseModel):
    request_summary: str
    code: str
    tests: str
    policy_verdict: PolicyVerdict
    tests_passed: bool
    test_output: str
    exit_code: int
    idempotency_key: str
    tier: str = Field(default="primary", description="Which tier served this: primary, fallback, template, degraded")
    error: str = ""


# ── Metering (R4) ───────────────────────────────────────────────────────────

class AgentMetrics(BaseModel):
    agent_name: str
    model_used: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_seconds: float = 0.0
