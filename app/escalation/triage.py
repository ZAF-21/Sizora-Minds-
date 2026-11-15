"""
R3: Triage — a single LLM call that returns task type, language, sentiment, urgency, wants_human.
"""

from __future__ import annotations
from langchain_groq import ChatGroq
from app.models import TriageResult
from app.config import LLM_CONFIG

TRIAGE_PROMPT = """\
You are a request triage agent. Analyze the user's message and classify it.
Respond ONLY with a JSON object with these fields:
- task_type: one of "python_function", "sql_query", "general_code", "unsupported"
- language: programming language (default "python")
- sentiment: one of "calm", "frustrated", "angry", "desperate"
- urgency: one of "low", "medium", "high", "critical"
- wants_human: true if user explicitly asks for a human/person/agent, false otherwise

Rules:
- Detect if the user explicitly asks for a human ("get me a human", "talk to a person", "escalate")
- Detect sentiment from tone: ALL CAPS + !!! = angry, polite request = calm
- Detect urgency: deadline mentioned = high, emergency + angry = critical

User message: {request}
"""


def create_triage_agent():
    llm = ChatGroq(
        model=LLM_CONFIG.small_model,
        temperature=LLM_CONFIG.temperature,
        max_tokens=LLM_CONFIG.max_tokens,
    )
    return llm.with_structured_output(TriageResult, method="json_mode")


def triage_request(request: str) -> TriageResult:
    agent = create_triage_agent()
    return agent.invoke(TRIAGE_PROMPT.format(request=request))
