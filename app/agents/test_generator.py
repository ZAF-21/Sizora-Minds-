"""
Test Generation Agent — produces pytest-style unit tests for generated code.
"""

from __future__ import annotations
import ast
from langchain_groq import ChatGroq
from app.models import Requirements, GeneratedTests
from app.config import LLM_CONFIG

TEST_GEN_PROMPT = """\
You are a test engineer. Write pytest-style unit tests for the following Python function.
Respond ONLY with a JSON object with these fields:
- test_code: the complete test file as a string (no markdown, no code blocks)
- num_tests: the number of test cases written

Function code:
{code}

Requirements:
- Function name: {function_name}
- Description: {description}
- Edge cases: {edge_cases}

Rules:
- Write at least 5 test cases
- Include normal cases, edge cases, and boundary cases
- Use descriptive test function names (test_<function_name>_<scenario>)
- Use assert statements
- The function lives in a module named `solution`. Start the file with: from solution import {function_name}
- Do NOT copy or redefine the function in the test file — test the imported one
- Keep it short: 5-6 focused tests, no comments or docstrings
- Do NOT use markdown code blocks, just raw Python code in the test_code field
"""


def create_test_gen_agent():
    llm = ChatGroq(
        model=LLM_CONFIG.large_model,
        temperature=LLM_CONFIG.temperature,
        max_tokens=LLM_CONFIG.max_tokens,
    )
    return llm.with_structured_output(GeneratedTests, method="json_mode")


def generate_tests(code: str, requirements: Requirements) -> GeneratedTests:
    agent = create_test_gen_agent()
    result = agent.invoke(TEST_GEN_PROMPT.format(
        code=code,
        function_name=requirements.function_name,
        description=requirements.description,
        edge_cases="; ".join(requirements.edge_cases) or "None specified",
    ))
    result.test_code = ensure_tests_import_solution(result.test_code, code)
    return result


def ensure_tests_import_solution(test_code: str, code: str) -> str:
    """Make sure the tests exercise the generated code, not a copy: drop any top-level redefinition
    of a function/class from `code` and import everything from `solution` instead."""
    try:
        defined = {n.name for n in ast.parse(code).body
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        tree = ast.parse(test_code)
    except SyntaxError:
        return test_code
    kept = [n for n in tree.body
            if not (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in defined)]
    if len(kept) == len(tree.body) and "from solution import" in test_code:
        return test_code
    tree.body = kept
    return "from solution import *\n" + ast.unparse(tree) + "\n"
