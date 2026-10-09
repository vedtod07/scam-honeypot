"""
guardrail.py — Scam Honeypot Phase 1
Prevents the persona from leaking sensitive-looking data (OTPs, Aadhaar-like
numbers, card numbers) in its replies. Canary values are always allowed.
"""

import json
import logging
import re
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canary loader
# ---------------------------------------------------------------------------

def load_canary(path: str = "canary.json") -> dict:
    """Load canary data from JSON file."""
    p = Path(path)
    if not p.exists():
        # Try relative to this file's directory
        p = Path(__file__).parent / path
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Block patterns
# ---------------------------------------------------------------------------

_BLOCK_PATTERNS = [
    (re.compile(r"\b\d{6}\b"), "OTP-like 6-digit number"),
    (re.compile(r"\b\d{12}\b"), "Aadhaar-like 12-digit number"),
    (re.compile(r"\b\d{16}\b"), "Card-like 16-digit number"),
    (re.compile(r"\b\d{9,18}\b"), "Long numeric sequence (9-18 digits)"),
]


def _build_canary_values(canary: dict) -> set[str]:
    """Extract all digit-strings from canary values to whitelist."""
    values = set()
    for v in canary.values():
        if isinstance(v, str):
            values.add(v)
            # Also add just the digit sequences within
            for m in re.finditer(r"\d+", v):
                values.add(m.group())
    return values


def check_reply(text: str, canary: dict) -> tuple[bool, str, list[str]]:
    """
    Check if the reply text is safe (no sensitive-looking data outside canary).

    Returns:
        (allowed, redacted_text, reasons)
        - allowed: True if text is safe to send
        - redacted_text: text with offending spans replaced by [REDACTED]
        - reasons: list of reason strings (empty if allowed)
    """
    canary_values = _build_canary_values(canary)
    reasons = []
    redacted = text

    for pattern, description in _BLOCK_PATTERNS:
        for match in pattern.finditer(text):
            matched_str = match.group()
            # Allow if it's literally a canary value or substring of one
            is_canary = matched_str in canary_values or any(
                matched_str in cv for cv in canary_values
            )
            if not is_canary:
                reasons.append(f"Found {description}: {matched_str!r}")

    # Perform redaction pass (replace non-canary matches)
    def _redact_match(m: re.Match, pat_desc: str) -> str:
        matched_str = m.group()
        is_canary = matched_str in canary_values or any(
            matched_str in cv for cv in canary_values
        )
        return matched_str if is_canary else "[REDACTED]"

    for pattern, description in _BLOCK_PATTERNS:
        redacted = pattern.sub(
            lambda m, pd=description: _redact_match(m, pd), redacted
        )

    allowed = len(reasons) == 0
    return allowed, redacted, reasons


# ---------------------------------------------------------------------------
# safe_reply: retry wrapper
# ---------------------------------------------------------------------------

# Module-level leak log (inspectable in tests)
_last_leak_log: dict = {}


def safe_reply(
    generate_fn: Callable[[], str],
    canary: dict,
    max_retries: int = 1,
) -> str:
    """
    Call generate_fn(), run check_reply. If blocked, retry once with a safety
    note appended. If still blocked after retries, return the redacted text.
    """
    global _last_leak_log
    _last_leak_log = {}

    reply = generate_fn()
    allowed, redacted, reasons = check_reply(reply, canary)

    if allowed:
        return reply

    logger.warning("Guardrail blocked reply (attempt 1). Reasons: %s", reasons)
    # Record the block even if the retry comes back clean, so it is counted.
    _last_leak_log = {"leak_blocked": True, "reasons": reasons}

    if max_retries > 0:
        # Retry: generate_fn doesn't accept arguments, so the caller is
        # responsible for injecting the safety note into the next prompt.
        # Here we retry once unconditionally.
        try:
            reply2 = generate_fn()
            allowed2, redacted2, reasons2 = check_reply(reply2, canary)
            if allowed2:
                return reply2
            # Still blocked — log and return redacted
            logger.warning("Guardrail blocked reply (attempt 2). Reasons: %s", reasons2)
            _last_leak_log = {"leak_blocked": True, "reasons": reasons2}
            return redacted2
        except Exception as exc:
            logger.error("Retry generate_fn failed: %s", exc)

    _last_leak_log = {"leak_blocked": True, "reasons": reasons}
    return redacted
