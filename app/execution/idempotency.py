"""
R2: Idempotency — same (user, code, tests) never runs twice.
"""

from __future__ import annotations
import hashlib
from app.models import ExecutionReport


class IdempotencyStore:
    """Deduplicate execution based on hash(user_id, code, tests)."""

    def __init__(self):
        self._cache: dict[str, ExecutionReport] = {}

    @staticmethod
    def make_key(user_id: str, code: str, tests: str) -> str:
        payload = f"{user_id}::{code}::{tests}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, key: str) -> ExecutionReport | None:
        return self._cache.get(key)

    def store(self, key: str, report: ExecutionReport) -> None:
        self._cache[key] = report

    def has(self, key: str) -> bool:
        return key in self._cache


IDEMPOTENCY_STORE = IdempotencyStore()
