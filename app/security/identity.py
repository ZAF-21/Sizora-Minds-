"""
R1: Identity management — user id and role come from config, never from the message.
"""

from __future__ import annotations
from app.config import UserConfig, get_user_config


def get_identity(user_id: str) -> UserConfig:
    """Get user identity from config. Raises PermissionError for unknown users."""
    return get_user_config(user_id)


def is_instructor(user_id: str) -> bool:
    return get_user_config(user_id).role == "instructor"


def is_student(user_id: str) -> bool:
    return get_user_config(user_id).role == "student"


def validate_role_from_config(user_id: str, claimed_role: str | None = None) -> str:
    """Always return the role from config, ignoring any claimed role in the message."""
    config = get_user_config(user_id)
    return config.role
