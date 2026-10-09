"""
tests/test_guardrail.py — Offline tests for guardrail.py
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from guardrail import check_reply, load_canary, safe_reply, _last_leak_log
import guardrail


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canary():
    return load_canary(str(Path(__file__).parent.parent / "canary.json"))


# ---------------------------------------------------------------------------
# Block tests
# ---------------------------------------------------------------------------

def test_blocks_otp():
    canary = _canary()
    allowed, redacted, reasons = check_reply("Your OTP is 483920", canary)
    assert not allowed
    assert "[REDACTED]" in redacted
    assert any("6-digit" in r or "OTP" in r or "digit" in r for r in reasons)


def test_blocks_aadhaar():
    canary = _canary()
    allowed, redacted, reasons = check_reply(
        "Please share Aadhaar 123456789012 for verification", canary
    )
    assert not allowed
    assert "[REDACTED]" in redacted


def test_blocks_card():
    canary = _canary()
    allowed, redacted, reasons = check_reply(
        "My card number is 4111111111111111", canary
    )
    assert not allowed
    assert "[REDACTED]" in redacted


# ---------------------------------------------------------------------------
# Allow tests
# ---------------------------------------------------------------------------

def test_allows_canary_upi():
    canary = _canary()
    # canary UPI: ramesh.test@okbank
    text = "Haan ji, mera UPI ID hai ramesh.test@okbank, kya aap confirm kar sakte hain?"
    allowed, redacted, reasons = check_reply(text, canary)
    assert allowed, f"Should have allowed canary UPI, reasons: {reasons}"


def test_allows_canary_phone():
    canary = _canary()
    # canary phone: +91-9800000001
    text = "Mera phone number hai +91-9800000001, please call me back"
    allowed, redacted, reasons = check_reply(text, canary)
    assert allowed, f"Should have allowed canary phone, reasons: {reasons}"


def test_allows_normal_text():
    canary = _canary()
    text = "Haan ji theek hai, par mujhe samajh nahi aa raha. Kaunsa button dabana hai?"
    allowed, redacted, reasons = check_reply(text, canary)
    assert allowed, f"Normal text should be allowed, reasons: {reasons}"


# ---------------------------------------------------------------------------
# safe_reply
# ---------------------------------------------------------------------------

def test_safe_reply_passes_clean():
    canary = _canary()
    gen = MagicMock(return_value="Beta, which button do I press?")
    result = safe_reply(gen, canary)
    assert result == "Beta, which button do I press?"
    assert gen.call_count == 1


def test_safe_reply_retries_once_and_returns_redacted():
    """Generator that always returns a leaky reply: retry happens, returns redacted."""
    canary = _canary()
    leaky_reply = "Please use OTP 483920 for verification"
    gen = MagicMock(return_value=leaky_reply)

    result = safe_reply(gen, canary, max_retries=1)

    # Should have retried once (total 2 calls)
    assert gen.call_count == 2
    # Result should be redacted
    assert "[REDACTED]" in result
    # leak_blocked should be logged
    assert guardrail._last_leak_log.get("leak_blocked") is True


def test_safe_reply_leak_blocked_logged():
    canary = _canary()
    gen = MagicMock(return_value="Your Aadhaar 123456789012 please")
    safe_reply(gen, canary, max_retries=1)
    assert guardrail._last_leak_log.get("leak_blocked") is True
    assert len(guardrail._last_leak_log.get("reasons", [])) > 0
