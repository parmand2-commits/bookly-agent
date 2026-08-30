"""Structured JSON logging for turns and escalations. Every record is redacted before it touches disk."""

import json
import re

from src import config

TURNS_PATH = config.LOGS_DIR / "turns.jsonl"
ESCALATIONS_PATH = config.LOGS_DIR / "escalations.log"

# Frozen turn schema. Do not add fields here without an explicit instruction to do so --
# rejected_escalation_proposal and escalation_triggers were each added on one such instruction,
# not as drift.
TURN_FIELDS = {
    "conversation_id",
    "turn",
    "timestamp",
    "customer_id",
    "intent",
    "procedure",
    "retrieval",
    "tools_called",
    "model",
    "latency_ms",
    "tokens_in",
    "tokens_out",
    "cost_usd",
    "escalated",
    "escalation_reason",
    "escalation_triggers",
    "rejected_escalation_proposal",
}

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_LAST4_RE = re.compile(r"(?i)(ending(?: in)?|last4[:\s]*|card ending)\s*(\d{4})\b")


def _redact(text):
    """Replace email addresses and 4-digit payment fragments (identified by their surrounding context) in text."""
    text = _EMAIL_RE.sub("[redacted-email]", text)
    text = _LAST4_RE.sub(lambda m: f"{m.group(1)}[redacted-last4]", text)
    return text


def _redact_value(value):
    """Recursively apply _redact to every string found inside a JSON-shaped value (dict, list, or scalar)."""
    if isinstance(value, str):
        return _redact(value)
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    return value


def _append_line(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_redact_value(record)) + "\n")


def log_turn(record):
    """Append one redacted JSON line to logs/turns.jsonl. record's keys must exactly match the frozen schema."""
    if set(record) != TURN_FIELDS:
        missing = TURN_FIELDS - set(record)
        extra = set(record) - TURN_FIELDS
        raise ValueError(f"turn record does not match frozen schema (missing={missing}, extra={extra})")
    try:
        _append_line(TURNS_PATH, record)
    except OSError:
        pass


def log_escalation(record):
    """Append one redacted JSON line to logs/escalations.log."""
    try:
        _append_line(ESCALATIONS_PATH, record)
    except OSError:
        pass
