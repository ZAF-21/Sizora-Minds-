"""
Code Generation Agent — produces Python code from structured requirements.
"""

from __future__ import annotations
from langchain_groq import ChatGroq
from app.models import Requirements, GeneratedCode
from app.config import LLM_CONFIG

CODE_GEN_PROMPT = """\
You are an expert Python code generator. Generate a complete, working Python function.
Respond ONLY with a JSON object with these fields:
- code: the complete Python function code as a string (no markdown, no code blocks)
- explanation: a brief one-line explanation
- time_complexity: Big-O time complexity (e.g. "O(n)", "O(n log n)", "O(1)")
- space_complexity: Big-O space complexity (e.g. "O(n)", "O(1)")

Function name: {function_name}
Parameters: {parameters}
Return type: {return_type}
Description: {description}
Edge cases to handle: {edge_cases}
Constraints: {constraints}

Rules:
- Write clean, production-quality Python code with type hints
- Keep it concise: a one-line docstring, no inline comments, no example usage (output is size-limited)
- Handle the edge cases listed
- Do NOT include any imports of os, sys, subprocess, shutil, or pathlib
- Do NOT use eval, exec, compile, __import__, globals or locals — implement logic explicitly
  (e.g. a calculator takes two numbers and an operator string and dispatches with if/elif or a dict)
- Do NOT include any file I/O, network calls, or system commands
- Return ONLY the function code in the "code" field, no test code
- Always analyze and include time_complexity and space_complexity
"""


def create_code_gen_agent():
    llm = ChatGroq(
        model=LLM_CONFIG.large_model,
        temperature=LLM_CONFIG.temperature,
        max_tokens=LLM_CONFIG.code_max_tokens,
    )
    return llm.with_structured_output(GeneratedCode, method="json_mode")


def generate_code(requirements: Requirements) -> GeneratedCode:
    agent = create_code_gen_agent()
    params_str = ", ".join(
        f"{p.name}: {p.type_hint}" for p in requirements.parameters
    ) if requirements.parameters else "No explicit parameters — infer from description"

    return agent.invoke(CODE_GEN_PROMPT.format(
        function_name=requirements.function_name,
        parameters=params_str,
        return_type=requirements.return_type,
        description=requirements.description,
        edge_cases="; ".join(requirements.edge_cases) or "None specified",
        constraints="; ".join(requirements.constraints) or "None specified",
    ))
