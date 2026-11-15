"""
R1 tests: Identity — role from config, not from message.
"""

import pytest
from app.config import get_user_config, USERS
from app.security.identity import validate_role_from_config, is_instructor, is_student


class TestIdentity:
    def test_student_role_from_config(self):
        config = get_user_config("student_a")
        assert config.role == "student"

    def test_instructor_role_from_config(self):
        config = get_user_config("instructor_1")
        assert config.role == "instructor"

    def test_unknown_user_raises(self):
        with pytest.raises(PermissionError):
            get_user_config("hacker_999")

    def test_claimed_role_ignored(self):
        """Even if user claims to be instructor, config role is returned."""
        role = validate_role_from_config("student_a", claimed_role="instructor")
        assert role == "student"

    def test_is_instructor(self):
        assert is_instructor("instructor_1") is True
        assert is_instructor("student_a") is False

    def test_is_student(self):
        assert is_student("student_a") is True
        assert is_student("instructor_1") is False


class TestQuota:
    def test_quota_tracker_basic(self):
        from app.security.quota import QuotaTracker
        tracker = QuotaTracker()
        assert tracker.check_quota("student_a") is True
        assert tracker.remaining("student_a") == 20

    def test_quota_decrements(self):
        from app.security.quota import QuotaTracker
        tracker = QuotaTracker()
        tracker.record_run("student_a")
        assert tracker.remaining("student_a") == 19


class TestAccessControl:
    def test_run_isolation(self):
        from app.security.access_control import RunStore, RunRecord
        store = RunStore()
        store.add_run(RunRecord("r1", "user_a", "test", "code", "pass", "2024-01-01"))
        store.add_run(RunRecord("r2", "user_b", "test", "code", "pass", "2024-01-01"))

        assert len(store.get_runs("user_a")) == 1
        assert len(store.get_runs("user_b")) == 1
        assert len(store.get_runs("user_c")) == 0  # "missing" same as "not yours"

    def test_run_by_id_isolation(self):
        from app.security.access_control import RunStore, RunRecord
        store = RunStore()
        store.add_run(RunRecord("r1", "user_a", "test", "code", "pass", "2024-01-01"))

        assert store.get_run_by_id("user_a", "r1") is not None
        assert store.get_run_by_id("user_b", "r1") is None  # Can't access other user's run
