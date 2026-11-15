"""
R7: SQL validator — parse with sqlglot, enforce rules in code.
One statement, SELECT only, table allow-list, enforced LIMIT.
"""

from __future__ import annotations
import sqlglot
from sqlglot import expressions as exp
from app.sql.database import ALLOWED_TABLES, BLOCKED_TABLES, MAX_LIMIT


def validate_sql(sql: str) -> tuple[str, list[str]]:
    """
    Validate and sanitize a SQL query. Returns (safe_sql, errors).
    If errors is non-empty, the query must NOT be executed.
    The returned safe_sql is regenerated from the parsed AST — not the raw input.
    """
    errors: list[str] = []

    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except Exception as e:
        return sql, [f"Could not parse the SQL: {e}"]

    if len(statements) == 0:
        return sql, ["Empty query."]

    if len(statements) > 1:
        return sql, ["Only one SQL statement is allowed at a time."]

    tree = statements[0]

    if not isinstance(tree, exp.Select):
        union_types = (exp.Union, exp.Intersect, exp.Except)
        if isinstance(tree, union_types):
            pass
        else:
            return sql, [f"Only SELECT queries are allowed. Got: {type(tree).__name__}"]

    cte_aliases = {cte.alias.lower() for cte in tree.find_all(exp.CTE) if cte.alias}
    tables_used = {t.name.lower() for t in tree.find_all(exp.Table)} - cte_aliases

    for t in tables_used:
        if t in BLOCKED_TABLES:
            return sql, [f"Access to the '{t}' table is not allowed — it contains private data."]

    unknown = tables_used - ALLOWED_TABLES
    if unknown:
        return sql, [f"Unknown table(s): {', '.join(unknown)}. Available: {', '.join(sorted(ALLOWED_TABLES))}"]

    limit_node = tree.find(exp.Limit)
    if limit_node is None:
        tree = tree.limit(MAX_LIMIT)
    else:
        try:
            limit_val = int(limit_node.expression.this)
            if limit_val > MAX_LIMIT:
                limit_node.expression.set("this", str(MAX_LIMIT))
        except (ValueError, AttributeError):
            pass

    safe_sql = tree.sql(dialect="sqlite")
    return safe_sql, []
