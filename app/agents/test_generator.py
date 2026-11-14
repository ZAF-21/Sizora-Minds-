"""
Test Generation Agent — produces pytest-style unit tests for generated code.
"""

from __future__ import annotations
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
- The test file MUST include the function definition at the top, then the tests
- Do NOT use markdown code blocks, just raw Python code in the test_code field
"""


def create_test_gen_agent():
    llm = ChatGroq(
        model=LLM_CONFIG.large_model,
        temperature=LLM_CONFIG.temperature,
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
    return result
