"""
R7: SQL Code Agent — generates SQL from natural language, validates, then executes.
Instructor (admin) role only (from config): SELECT/INSERT/UPDATE on every table;
DELETE/DROP/TRUNCATE are always blocked, and sensitive columns are masked in results.
"""

from __future__ import annotations
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from app.config import LLM_CONFIG
from app.sql.validator import validate_sql
from app.sql.database import run_readonly, run_write, ensure_sample_db

# Column name -> masking function for PII in query results
SENSITIVE_COLUMNS = {
    "email": lambda v: (v[0] + "***@" + v.split("@", 1)[1]) if "@" in v and v else "***",
    "phone": lambda v: "*" * max(len(v) - 4, 0) + v[-4:],
    "aadhaar": lambda v: "XXXX-XXXX-" + v[-4:],
    "password_hash": lambda v: "[REDACTED]",
}


class SQLQuery(BaseModel):
    sql: str = Field(description="The SQL query")
    explanation: str = Field(default="", description="Brief explanation of what the query does")


SQL_GEN_PROMPT = """\
You are a SQL expert. Generate a single SQLite query for the user's request.
Respond ONLY with a JSON object with fields: sql, explanation.

Available tables:
- employees (id, name, department, salary, hire_date)
- sales (id, employee_id, product, amount, sale_date, region)
- users (id, email, phone, aadhaar, password_hash)

Rules:
- You may write SELECT, INSERT or UPDATE statements
- NEVER write DELETE, DROP, TRUNCATE, ALTER or CREATE statements
- Write exactly one statement
- SELECT queries must include a LIMIT clause (max 1000)
- Use proper SQLite syntax

User request: {request}
"""


def create_sql_agent():
    llm = ChatGroq(
        model=LLM_CONFIG.small_model,
        temperature=LLM_CONFIG.temperature,
        max_tokens=LLM_CONFIG.max_tokens,
    )
    return llm.with_structured_output(SQLQuery, method="json_mode")


def generate_sql(request: str) -> SQLQuery:
    agent = create_sql_agent()
    return agent.invoke(SQL_GEN_PROMPT.format(request=request))


def mask_sensitive_columns(rows: list[dict]) -> list[dict]:
    """Mask PII columns (by column name) so results never show raw personal data."""
    masked = []
    for row in rows:
        masked.append({
            k: (SENSITIVE_COLUMNS[k.lower()](str(v)) if k.lower() in SENSITIVE_COLUMNS and v is not None else v)
            for k, v in row.items()
        })
    return masked


def execute_validated_sql(sql: str, user_role: str) -> dict:
    """Validate a SQL string for the role, then execute it. Shared by the LLM pipeline and tests."""
    safe_sql, errors = validate_sql(sql, role=user_role)
    if errors:
        return {"status": "denied", "error": errors[0], "sql": sql, "results": None}

    is_write = safe_sql.lstrip().upper().startswith(("INSERT", "UPDATE"))
    try:
        ensure_sample_db()
        results = run_write(safe_sql) if is_write else mask_sensitive_columns(run_readonly(safe_sql))
    except Exception as e:
        return {"status": "error", "error": f"Query execution failed: {str(e)[:80]}", "sql": safe_sql, "results": None}

    return {"status": "success", "sql": safe_sql, "results": results, "is_write": is_write, "error": None}


def run_sql_pipeline(request: str, user_role: str) -> dict:
    """
    Full SQL pipeline: role check → generate → validate → execute.
    Returns dict with status, sql, results, errors (and is_write/explanation on success).
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

    result = execute_validated_sql(query.sql, user_role)
    if result["status"] == "success":
        result["explanation"] = query.explanation
    return result
