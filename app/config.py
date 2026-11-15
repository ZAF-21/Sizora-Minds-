"""
CodeForge configuration — user identity and role come from HERE, never from the message.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

# Verify TLS with the OS trust store (macOS Keychain / Windows cert store). Python 3.14's stricter
# X.509 checks reject some corporate proxy CAs that the OS itself trusts. Verification stays on.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# ── User configuration (R1: identity from config, not from message) ──────────

@dataclass(frozen=True)
class UserConfig:
    user_id: str
    role: str  # "student" or "instructor"
    max_runs_per_hour: int = 20

# Pre-defined users — in production this comes from an auth service / JWT
USERS: dict[str, UserConfig] = {
    "student_a": UserConfig(user_id="student_a", role="student", max_runs_per_hour=20),
    "student_b": UserConfig(user_id="student_b", role="student", max_runs_per_hour=20),
    "student_c": UserConfig(user_id="student_c", role="student", max_runs_per_hour=20),
    "instructor_1": UserConfig(user_id="instructor_1", role="instructor", max_runs_per_hour=100),
}

DEFAULT_USER = "student_a"

def get_user_config(user_id: str | None = None) -> UserConfig:
    uid = user_id or DEFAULT_USER
    if uid not in USERS:
        raise PermissionError(f"Unknown user: {uid}")
    return USERS[uid]


# ── LLM configuration ───────────────────────────────────────────────────────

@dataclass
class LLMConfig:
    primary_model: str = "qwen/qwen3.8-27b"
    small_model: str = "qwen/qwen3.8-27b"
    large_model: str = "qwen/qwen3.8-27b"
    fallback_model: str = "allam-2-7b"
    temperature: float = 0.0
    max_retries: int = 3
    # Groq free tier allows ~1000 output tokens/minute; an uncapped request reserves 2048 and gets a 429.
    max_tokens: int = 600
    code_max_tokens: int = 950  # code generation needs the most room; must stay under the 1000/min cap

LLM_CONFIG = LLMConfig()

# ── Execution limits ─────────────────────────────────────────────────────────

SANDBOX_TIMEOUT_SECONDS = 10
SANDBOX_MAX_MEMORY_MB = 256
MAX_GENERATED_CODE_LENGTH = 5000
MAX_LIMIT_SQL = 1000

# ── Cost tracking (Groq is free, but we track for demo) ─────────────────────

MODEL_COSTS = {
    "qwen/qwen3.8-27b": {"input": 0.00, "output": 0.00},
    "allam-2-7b": {"input": 0.00, "output": 0.00},
}
