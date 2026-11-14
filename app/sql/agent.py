"""
R7: SQL Code Agent — generates SQL from natural language, validates, runs read-only.
Instructor role only (from config).
"""

from __future__ import annotations
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from app.config import LLM_CONFIG
from app.sql.validator import validate_sql
from app.sql.database import run_readonly, init_sample_db, ALLOWED_TABLES


class SQLQuery(BaseModel):
    sql: str = Field(description="The SQL SELECT query")
    explanation: str = Field(default="", description="Brief explanation of what the query does")


SQL_GEN_PROMPT = """\
You are a SQL expert. Generate a SQLite SELECT query for the user's request.
Respond ONLY with a JSON object with fields: sql, explanation.

Available tables:
- employees (id, name, department, salary, hire_date)
- sales (id, employee_id, product, amount, sale_date, region)

Rules:
- Only write SELECT queries
- Do NOT access the 'users' table — it contains private data
- Always include a LIMIT clause (max 1000)
- Use proper SQLite syntax

User request: {request}
"""


def create_sql_agent():
    llm = ChatGroq(
        model=LLM_CONFIG.small_model,
        temperature=LLM_CONFIG.temperature,
    )
    return llm.with_structured_output(SQLQuery, method="json_mode")


def generate_sql(request: str) -> SQLQuery:
    agent = create_sql_agent()
    return agent.invoke(SQL_GEN_PROMPT.format(request=request))


def run_sql_pipeline(request: str, user_role: str) -> dict:
    """
    Full SQL pipeline: role check → generate → validate → run read-only.
    Returns dict with status, sql, results, errors.
    """
    if user_role != "instructor":
        return {
            "status": "denied",
            "error": "SQL queries are only available for instructor accounts.",
            "sql": None,
            "results": None,
        }

    try:
        query = generate_sql(request)
    except Exception as e:
        return {
            "status": "error",
            "error": f"Could not generate a SQL query: {str(e)[:80]}",
            "sql": None,
            "results": None,
        }

    safe_sql, errors = validate_sql(query.sql)

    if errors:
        return {
            "status": "denied",
            "error": errors[0],
            "sql": query.sql,
            "results": None,
        }

    try:
        init_sample_db()
        results = run_readonly(safe_sql)
        return {
            "status": "success",
            "sql": safe_sql,
            "explanation": query.explanation,
            "results": results,
            "error": None,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Query execution failed: {str(e)[:80]}",
            "sql": safe_sql,
            "results": None,
        }
