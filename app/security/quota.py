"""
R1: Per-user run quota enforcement.
"""

from __future__ import annotations
import time
from collections import defaultdict
from app.config import get_user_config


class QuotaTracker:
    """Track per-user run counts within a sliding window."""

    def __init__(self):
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def _clean_old(self, user_id: str, window_seconds: int = 3600) -> None:
        cutoff = time.time() - window_seconds
        self._timestamps[user_id] = [
            t for t in self._timestamps[user_id] if t > cutoff
        ]

    def check_quota(self, user_id: str) -> bool:
        """Return True if user is within quota, False if exceeded."""
        config = get_user_config(user_id)
        self._clean_old(user_id)
        return len(self._timestamps[user_id]) < config.max_runs_per_hour

    def record_run(self, user_id: str) -> None:
        self._timestamps[user_id].append(time.time())

    def remaining(self, user_id: str) -> int:
        config = get_user_config(user_id)
        self._clean_old(user_id)
        return max(0, config.max_runs_per_hour - len(self._timestamps[user_id]))


QUOTA_TRACKER = QuotaTracker()
