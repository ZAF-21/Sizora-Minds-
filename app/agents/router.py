"""
Router/Parser Agent — classifies the request using structured output.
"""

from __future__ import annotations
from langchain_groq import ChatGroq
from app.models import RoutingResult, TaskType
from app.config import LLM_CONFIG

ROUTER_PROMPT = """\
You are a code-request router. Given a user request, classify it.
Respond ONLY with a JSON object with these fields:
- task_type: one of "python_function", "sql_query", "general_code", "unsupported"
- language: the programming language (default "python")
- is_context_free: true if the request is self-contained, false if it references prior conversation
- summary: a brief summary of what the user wants

Rules:
- If the request asks for a Python function or script, set task_type to "python_function"
- If the request asks for a SQL query, set task_type to "sql_query"
- If the request asks for code in another language, set task_type to "general_code"
- If the request is not about code at all, set task_type to "unsupported"

User request: {request}
"""


def create_router_agent():
    llm = ChatGroq(
        model=LLM_CONFIG.small_model,
        temperature=LLM_CONFIG.temperature,
    )
    return llm.with_structured_output(RoutingResult, method="json_mode")


def route_request(request: str) -> RoutingResult:
    agent = create_router_agent()
    return agent.invoke(ROUTER_PROMPT.format(request=request))
