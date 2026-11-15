"""
Structured audit log for pipeline events (R1: privacy).

Rule: events are logged only AFTER PII masking. Callers pass already-masked text, and
`log_event` masks every string field again before writing, so a raw email, card number,
Aadhaar number or API key can never reach the log even if a caller slips up.

Output is one JSON object per line on the "codeforge.events" logger, e.g.
    {"event": "request_received", "user": "student_a", "request": "[SECRET] fix my code", "pii_masked": true}
"""

from __future__ import annotations
import json
import logging
import os
from typing import Any

from app.security.privacy import mask_pii

logger = logging.getLogger("codeforge.events")


def _mask_value(value: Any) -> Any:
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, dict):
        return {k: _mask_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_mask_value(v) for v in value]
    return value


def log_event(event: str, user_id: str, **fields: Any) -> None:
    """Write one masked, structured event line."""
    record = {"event": event, "user": user_id, **_mask_value(fields)}
    logger.info(json.dumps(record, default=str, ensure_ascii=False))


def configure_logging() -> None:
    """Console logging for the app; level comes from CODEFORGE_LOG_LEVEL (see .env.example)."""
    level = os.getenv("CODEFORGE_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, level, logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s | %(message)s")
