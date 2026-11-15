"""
R1: PII masking — mask secrets and PII at ingress so they never reach the model, logs, or generated code.
"""

from __future__ import annotations
import re

# ── Luhn check for card number validation ────────────────────────────────────

def _luhn_ok(digits: str) -> bool:
    """Validate a card number using the Luhn algorithm. Prevents false positives on order refs."""
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0

_CARD_RE = re.compile(r"(?<!\d)(?:\d[\s-]?){12,18}\d(?!\d)")

def _mask_card(match: re.Match) -> str:
    """Only mask if the digits pass Luhn — so 16-digit order references survive."""
    digits = re.sub(r"\D", "", match.group())
    if 13 <= len(digits) <= 19 and _luhn_ok(digits):
        return "[CARD]"
    return match.group()

# ── Patterns ─────────────────────────────────────────────────────────────────

_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # API keys: OpenAI, Groq, Anthropic, Google, AWS, generic
    ("api_key", re.compile(r"\b(sk-[A-Za-z0-9_-]{20,})\b"), "[SECRET]"),
    ("api_key", re.compile(r"\b(gsk_[A-Za-z0-9_-]{20,})\b"), "[SECRET]"),
    ("api_key", re.compile(r"\b(sk-ant-[A-Za-z0-9_-]{20,})\b"), "[SECRET]"),
    ("api_key", re.compile(r"(AIza[A-Za-z0-9_-]{20,})"), "[SECRET]"),
    ("api_key", re.compile(r"\b(AKIA[A-Z0-9]{16})\b"), "[SECRET]"),

    # Email addresses
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),

    # Indian phone numbers: +91 followed by 10 digits, with optional separators
    ("phone", re.compile(r"\+91[\s-]?\d{5}[\s-]?\d{5}\b"), "[PHONE]"),
    # Generic 10-digit Indian mobile (starts with 6-9)
    ("phone", re.compile(r"\b[6-9]\d{9}\b"), "[PHONE]"),

    # Aadhaar numbers: exactly 12 digits with optional spaces/dashes
    ("aadhaar", re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[AADHAAR]"),

    # SSN (US)
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
]


def mask_pii(text: str) -> str:
    """Replace all PII/secrets in text with placeholder tokens."""
    # Cards first via Luhn-validated callback (before other numeric patterns)
    masked = _CARD_RE.sub(_mask_card, text)
    for _name, pattern, replacement in _PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked


def has_pii(text: str) -> bool:
    """Check if text contains any PII or secrets."""
    return mask_pii(text) != text


def get_masked_fields(text: str) -> list[str]:
    """Return list of PII types found in text."""
    found = []
    for name, pattern, _ in _PATTERNS:
        if pattern.search(text):
            found.append(name)
    return list(set(found))
