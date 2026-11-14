"""
Requirements Agent — extracts structured requirements from a code request.
"""

from __future__ import annotations
from langchain_groq import ChatGroq
from app.models import Requirements
from app.config import LLM_CONFIG

REQUIREMENTS_PROMPT = """\
You are a requirements extraction agent. Given a user's code request, extract structured requirements.
Respond ONLY with a JSON object with these fields:
- function_name: a clear snake_case function name
- parameters: a list of objects with "name", "type_hint", and "description"
- return_type: the return type hint (e.g. "bool", "int", "list[int]")
- description: what the function should do
- edge_cases: a list of edge cases to handle
- constraints: a list of explicit constraints from the user

User request: {request}
"""


def create_requirements_agent():
    llm = ChatGroq(
        model=LLM_CONFIG.small_model,
        temperature=LLM_CONFIG.temperature,
    )
    return llm.with_structured_output(Requirements, method="json_mode")


def extract_requirements(request: str) -> Requirements:
    agent = create_requirements_agent()
    return agent.invoke(REQUIREMENTS_PROMPT.format(request=request))
