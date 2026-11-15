"""
R1: Access control — per-user run isolation.
Functions that return past runs take no user argument; user comes from the session context.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RunRecord:
    run_id: str
    user_id: str
    request_summary: str
    code: str
    test_result: str
    timestamp: str


class RunStore:
    """In-memory store for run records, isolated per user."""

    def __init__(self):
        self._runs: dict[str, list[RunRecord]] = {}

    def add_run(self, record: RunRecord) -> None:
        if record.user_id not in self._runs:
            self._runs[record.user_id] = []
        self._runs[record.user_id].append(record)

    def get_runs(self, user_id: str) -> list[RunRecord]:
        """Get runs for a specific user. Returns empty list for unknown users
        (same as "not yours" — no information leak)."""
        return self._runs.get(user_id, [])

    def get_run_by_id(self, user_id: str, run_id: str) -> RunRecord | None:
        """Get a specific run only if it belongs to this user."""
        for run in self._runs.get(user_id, []):
            if run.run_id == run_id:
                return run
        return None


RUN_STORE = RunStore()
