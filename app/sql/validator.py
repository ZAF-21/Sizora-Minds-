"""
R7: SQL validator — parse with sqlglot, enforce rules in code.
One statement, enforced LIMIT on reads, role-based permissions:
- student:    SELECT only, table allow-list (users table blocked)
- instructor: SELECT / INSERT / UPDATE on every table; DELETE, DROP, TRUNCATE and schema changes blocked
"""

from __future__ import annotations
import sqlglot
from sqlglot import expressions as exp
from app.sql.database import ALLOWED_TABLES, BLOCKED_TABLES, ALL_TABLES, MAX_LIMIT

_READ_TYPES = (exp.Select, exp.Union, exp.Intersect, exp.Except)
_INSTRUCTOR_WRITE_TYPES = (exp.Insert, exp.Update)
_DESTRUCTIVE_TYPES = (exp.Delete, exp.Drop, exp.TruncateTable, exp.Alter, exp.Create, exp.Command)


def validate_sql(sql: str, role: str = "student") -> tuple[str, list[str]]:
    """
    Validate and sanitize a SQL query. Returns (safe_sql, errors).
    If errors is non-empty, the query must NOT be executed.
    The returned safe_sql is regenerated from the parsed AST — not the raw input.
    """
    is_instructor = role == "instructor"

    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except Exception as e:
        return sql, [f"Could not parse the SQL: {e}"]

    statements = [s for s in statements if s is not None]
    if len(statements) == 0:
        return sql, ["Empty query."]

    if len(statements) > 1:
        return sql, ["Only one SQL statement is allowed at a time."]

    tree = statements[0]
    is_read = isinstance(tree, _READ_TYPES)

    if any(isinstance(node, _DESTRUCTIVE_TYPES) for node in tree.walk()):
        kind = (type(tree).__name__.upper().replace("TRUNCATETABLE", "TRUNCATE")
                if isinstance(tree, _DESTRUCTIVE_TYPES) else "Destructive")
        return sql, [f"{kind} statements are not allowed — CodeForge never deletes data or changes the schema."]

    if not is_read:
        if not (is_instructor and isinstance(tree, _INSTRUCTOR_WRITE_TYPES)):
            allowed = "SELECT, INSERT and UPDATE" if is_instructor else "SELECT"
            return sql, [f"Only {allowed} queries are allowed. Got: {type(tree).__name__}"]

    cte_aliases = {cte.alias.lower() for cte in tree.find_all(exp.CTE) if cte.alias}
    tables_used = {t.name.lower() for t in tree.find_all(exp.Table)} - cte_aliases

    if not is_instructor:
        for t in tables_used:
            if t in BLOCKED_TABLES:
                return sql, [f"Access to the '{t}' table is not allowed — it contains private data."]

    known = ALL_TABLES if is_instructor else ALLOWED_TABLES
    unknown = tables_used - known
    if unknown:
        return sql, [f"Unknown table(s): {', '.join(sorted(unknown))}. Available: {', '.join(sorted(known))}"]

    if is_read:
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
