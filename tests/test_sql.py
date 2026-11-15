"""
R7 tests: SQL validator — blocks attacks, allows legitimate queries.
"""

import pytest
from app.sql.validator import validate_sql
from app.sql.database import init_sample_db, run_readonly


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_sample_db()


class TestSQLValidatorBlocks:
    def test_block_delete(self):
        _, errors = validate_sql("DELETE FROM sales")
        assert errors

    def test_block_drop(self):
        _, errors = validate_sql("DROP TABLE sales")
        assert errors

    def test_block_update(self):
        _, errors = validate_sql("UPDATE sales SET amount = 0")
        assert errors

    def test_block_insert(self):
        _, errors = validate_sql("INSERT INTO sales VALUES (99,1,'x',0,'2024-01-01','x')")
        assert errors

    def test_block_multiple_statements(self):
        _, errors = validate_sql("SELECT * FROM sales; DROP TABLE sales")
        assert errors

    def test_block_users_table(self):
        _, errors = validate_sql("SELECT * FROM users")
        assert errors
        assert "private" in errors[0].lower() or "not allowed" in errors[0].lower()

    def test_block_users_via_join(self):
        _, errors = validate_sql("SELECT * FROM sales JOIN users ON sales.employee_id = users.id")
        assert errors

    def test_block_users_via_cte(self):
        _, errors = validate_sql("WITH x AS (SELECT * FROM users) SELECT * FROM x")
        assert errors

    def test_block_users_via_union(self):
        _, errors = validate_sql("SELECT id FROM sales UNION SELECT id FROM users")
        assert errors

    def test_block_pragma(self):
        _, errors = validate_sql("PRAGMA table_info(sales)")
        assert errors


class TestSQLValidatorAllows:
    def test_allow_simple_select(self):
        safe_sql, errors = validate_sql("SELECT * FROM sales LIMIT 10")
        assert not errors
        assert "SELECT" in safe_sql.upper()

    def test_allow_aggregate(self):
        safe_sql, errors = validate_sql("SELECT region, COUNT(*) FROM sales GROUP BY region LIMIT 10")
        assert not errors

    def test_allow_join_allowed_tables(self):
        safe_sql, errors = validate_sql(
            "SELECT e.name, s.product FROM employees e JOIN sales s ON e.id = s.employee_id LIMIT 10"
        )
        assert not errors

    def test_allow_cte_with_allowed_tables(self):
        safe_sql, errors = validate_sql(
            "WITH top_sales AS (SELECT * FROM sales WHERE amount > 5000) SELECT * FROM top_sales LIMIT 10"
        )
        assert not errors

    def test_allow_union_allowed_tables(self):
        safe_sql, errors = validate_sql(
            "SELECT product FROM sales UNION SELECT name FROM employees LIMIT 10"
        )
        assert not errors


class TestSQLLimitEnforcement:
    def test_adds_limit_when_missing(self):
        safe_sql, errors = validate_sql("SELECT * FROM sales")
        assert not errors
        assert "LIMIT" in safe_sql.upper()

    def test_clamps_high_limit(self):
        safe_sql, errors = validate_sql("SELECT * FROM sales LIMIT 10000000")
        assert not errors
        assert "10000000" not in safe_sql


class TestSQLExecution:
    def test_readonly_query_runs(self):
        rows = run_readonly("SELECT COUNT(*) as cnt FROM sales")
        assert rows[0]["cnt"] == 10

    def test_employee_count(self):
        rows = run_readonly("SELECT COUNT(*) as cnt FROM employees")
        assert rows[0]["cnt"] == 5


class TestInstructorSQL:
    """Instructors are admins: read/insert/update any table, never delete or drop; PII masked."""

    @pytest.fixture(autouse=True)
    def fresh_db(self):
        init_sample_db()
        yield
        init_sample_db()

    @pytest.mark.parametrize("sql", [
        "DELETE FROM sales",
        "DROP TABLE users",
        "TRUNCATE TABLE sales",
        "ALTER TABLE sales ADD COLUMN x INT",
        "UPDATE sales SET amount = 0; DROP TABLE sales",
        "PRAGMA table_info(sales)",
    ])
    def test_destructive_blocked_for_instructor(self, sql):
        _, errors = validate_sql(sql, role="instructor")
        assert errors

    @pytest.mark.parametrize("sql", [
        "SELECT * FROM users",
        "UPDATE employees SET salary = salary * 1.1 WHERE department = 'Sales'",
        "INSERT INTO sales VALUES (99, 1, 'x', 10, '2024-01-01', 'East')",
    ])
    def test_instructor_allowed(self, sql):
        _, errors = validate_sql(sql, role="instructor")
        assert not errors

    def test_student_rules_unchanged(self):
        assert validate_sql("SELECT * FROM users", role="student")[1]
        assert validate_sql("UPDATE sales SET amount = 0", role="student")[1]

    def test_update_persists(self):
        from app.sql.agent import execute_validated_sql
        res = execute_validated_sql("UPDATE employees SET salary = 1 WHERE id = 1", "instructor")
        assert res["status"] == "success" and res["results"][0]["rows_affected"] == 1
        assert run_readonly("SELECT salary FROM employees WHERE id = 1")[0]["salary"] == 1

    def test_users_pii_masked(self):
        from app.sql.agent import execute_validated_sql
        row = execute_validated_sql("SELECT * FROM users WHERE id = 1", "instructor")["results"][0]
        assert row["email"] == "a***@company.com"
        assert row["phone"] == "******3210"
        assert row["aadhaar"] == "XXXX-XXXX-0123"
        assert row["password_hash"] == "[REDACTED]"
