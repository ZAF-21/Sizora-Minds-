"""
R2 tests: Idempotency — same (user, code, tests) produces same key, runs once.
"""

import pytest
from app.execution.idempotency import IdempotencyStore
from app.models import ExecutionReport, PolicyVerdict


class TestIdempotency:
    def test_same_input_same_key(self):
        key1 = IdempotencyStore.make_key("user_a", "def f(): pass", "def test_f(): pass")
        key2 = IdempotencyStore.make_key("user_a", "def f(): pass", "def test_f(): pass")
        assert key1 == key2

    def test_different_user_different_key(self):
        key1 = IdempotencyStore.make_key("user_a", "def f(): pass", "def test_f(): pass")
        key2 = IdempotencyStore.make_key("user_b", "def f(): pass", "def test_f(): pass")
        assert key1 != key2

    def test_different_code_different_key(self):
        key1 = IdempotencyStore.make_key("user_a", "def f(): pass", "def test_f(): pass")
        key2 = IdempotencyStore.make_key("user_a", "def g(): pass", "def test_f(): pass")
        assert key1 != key2

    def test_store_and_retrieve(self):
        store = IdempotencyStore()
        report = ExecutionReport(
            request_summary="test",
            code="def f(): pass",
            tests="def test_f(): pass",
            policy_verdict=PolicyVerdict.ALLOW,
            tests_passed=True,
            test_output="1 passed",
            exit_code=0,
            idempotency_key="abc123",
        )
        key = IdempotencyStore.make_key("u", "c", "t")
        store.store(key, report)
        assert store.has(key)
        assert store.get(key) == report

    def test_miss_returns_none(self):
        store = IdempotencyStore()
        assert store.get("nonexistent") is None
