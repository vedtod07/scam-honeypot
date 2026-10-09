"""
tests/test_extractor.py — Offline tests for extractor.py
All tests run with no API key (LLM env vars cleared).
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from extractor import (
    detect_signals,
    extract,
    merge_indicators,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _no_llm_env(monkeypatch):
    """Clear LLM env vars so only regex path runs."""
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)


def _load_script(name: str) -> dict:
    p = Path(__file__).parent.parent / "scripts" / f"{name}.json"
    with p.open() as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Per-script ground-truth extraction tests (regex only)
# ---------------------------------------------------------------------------

def _make_message(script: dict) -> str:
    gt = script["ground_truth_indicators"]
    parts = [script["opening_message"]]
    for upi in gt.get("upi_ids", []):
        parts.append(f"Send payment to {upi}")
    for phone in gt.get("phone_numbers", []):
        parts.append(f"Call us at {phone}")
    for url in gt.get("urls", []):
        parts.append(f"Visit {url}")
    for acct in gt.get("account_numbers", []):
        parts.append(f"Transfer to account {acct}")
    return " ".join(parts)


@pytest.mark.parametrize("script_name", ["digital_arrest", "kyc", "courier", "upi_collect"])
def test_script_ground_truth_regex(monkeypatch, script_name):
    _no_llm_env(monkeypatch)
    script = _load_script(script_name)
    gt = script["ground_truth_indicators"]
    msg = _make_message(script)

    result = extract(msg)

    for upi in gt.get("upi_ids", []):
        assert upi in result["upi_ids"], f"Missing UPI {upi!r} in {result['upi_ids']}"
    for phone in gt.get("phone_numbers", []):
        assert phone in result["phone_numbers"], (
            f"Missing phone {phone!r} in {result['phone_numbers']}"
        )
    for url in gt.get("urls", []):
        assert url in result["urls"], f"Missing URL {url!r} in {result['urls']}"
    for acct in gt.get("account_numbers", []):
        assert acct in result["account_numbers"], (
            f"Missing account {acct!r} in {result['account_numbers']}"
        )


# ---------------------------------------------------------------------------
# Email vs UPI disambiguation
# ---------------------------------------------------------------------------

def test_email_not_upi(monkeypatch):
    _no_llm_env(monkeypatch)
    result = extract("Reach me at officer.rao@gmail.com or send to verify.rbi2026@okhdfc")
    assert "verify.rbi2026@okhdfc" in result["upi_ids"], "Should find okhdfc UPI"
    # gmail address must NOT be in upi_ids
    gmail_in = any("gmail" in uid for uid in result["upi_ids"])
    assert not gmail_in, f"Gmail address ended up in upi_ids: {result['upi_ids']}"


# ---------------------------------------------------------------------------
# Phone normalization
# ---------------------------------------------------------------------------

def test_phone_normalization_bare(monkeypatch):
    _no_llm_env(monkeypatch)
    result = extract("Call 9812345670 for help")
    assert "+91-9812345670" in result["phone_numbers"]


def test_phone_normalization_plus91(monkeypatch):
    _no_llm_env(monkeypatch)
    result = extract("Call +91 9812345670 for help")
    assert "+91-9812345670" in result["phone_numbers"]


# ---------------------------------------------------------------------------
# merge_indicators
# ---------------------------------------------------------------------------

def test_merge_indicators_union_dedup():
    a = {"upi_ids": ["a@paytm"], "phone_numbers": ["+91-9000000001"],
         "urls": [], "account_numbers": [], "claimed_identity": "Inspector X", "scam_type": "digital_arrest"}
    b = {"upi_ids": ["a@paytm", "b@ybl"], "phone_numbers": ["+91-9000000002"],
         "urls": ["http://x.example.com"], "account_numbers": [],
         "claimed_identity": None, "scam_type": "unknown"}
    merged = merge_indicators(a, b)
    assert merged["upi_ids"] == ["a@paytm", "b@ybl"]
    assert "+91-9000000001" in merged["phone_numbers"]
    assert "+91-9000000002" in merged["phone_numbers"]
    assert "http://x.example.com" in merged["urls"]


def test_merge_indicators_claimed_identity_precedence():
    a = {"upi_ids": [], "phone_numbers": [], "urls": [], "account_numbers": [],
         "claimed_identity": "Inspector X", "scam_type": "digital_arrest"}
    b = {"upi_ids": [], "phone_numbers": [], "urls": [], "account_numbers": [],
         "claimed_identity": None, "scam_type": "unknown"}
    merged = merge_indicators(a, b)
    assert merged["claimed_identity"] == "Inspector X"


def test_merge_indicators_scam_type_update():
    a = {"upi_ids": [], "phone_numbers": [], "urls": [], "account_numbers": [],
         "claimed_identity": None, "scam_type": "unknown"}
    b = {"upi_ids": [], "phone_numbers": [], "urls": [], "account_numbers": [],
         "claimed_identity": None, "scam_type": "kyc"}
    merged = merge_indicators(a, b)
    assert merged["scam_type"] == "kyc"


# ---------------------------------------------------------------------------
# LLM fallback (malformed JSON)
# ---------------------------------------------------------------------------

def test_llm_fallback_malformed_json(monkeypatch):
    """When LLM returns garbage, result should be regex-only with source='regex'."""
    monkeypatch.setenv("LLM_BASE_URL", "http://fake")
    monkeypatch.setenv("LLM_API_KEY", "fake")
    monkeypatch.setenv("LLM_MODEL", "fake-model")

    fake_choice = MagicMock()
    fake_choice.message.content = "THIS IS NOT JSON }{{"
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response

    with patch("extractor._get_llm_client", return_value=(fake_client, "fake-model")):
        result = extract(
            "Transfer Rs 2L to verify.rbi2026@okhdfc, call +91-9812345670"
        )

    assert result["source"] == "regex"
    assert "verify.rbi2026@okhdfc" in result["upi_ids"]
    assert "+91-9812345670" in result["phone_numbers"]


# ---------------------------------------------------------------------------
# Code fence JSON parsing
# ---------------------------------------------------------------------------

def test_code_fence_json(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://fake")
    monkeypatch.setenv("LLM_API_KEY", "fake")
    monkeypatch.setenv("LLM_MODEL", "fake-model")

    payload = {
        "upi_ids": ["verify.rbi2026@okhdfc"],
        "phone_numbers": ["+91-9812345670"],
        "urls": [],
        "account_numbers": [],
        "claimed_identity": "Inspector Rao",
        "scam_type": "digital_arrest",
        "confidence": 0.95,
    }
    fence_response = f"```json\n{json.dumps(payload)}\n```"

    fake_choice = MagicMock()
    fake_choice.message.content = fence_response
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response

    with patch("extractor._get_llm_client", return_value=(fake_client, "fake-model")):
        result = extract("Transfer to verify.rbi2026@okhdfc, call +91-9812345670")

    assert "verify.rbi2026@okhdfc" in result["upi_ids"]
    assert result["source"] == "llm+regex"


def test_trailing_prose_json(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://fake")
    monkeypatch.setenv("LLM_API_KEY", "fake")
    monkeypatch.setenv("LLM_MODEL", "fake-model")

    payload = {
        "upi_ids": ["fedex.clearance@ybl"],
        "phone_numbers": [],
        "urls": [],
        "account_numbers": [],
        "claimed_identity": None,
        "scam_type": "courier",
        "confidence": 0.8,
    }
    prose_response = f"Sure! Here is the JSON:\n{json.dumps(payload)}\nLet me know if you need anything else."

    fake_choice = MagicMock()
    fake_choice.message.content = prose_response
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response

    with patch("extractor._get_llm_client", return_value=(fake_client, "fake-model")):
        result = extract("Pay fedex.clearance@ybl for clearance")

    assert "fedex.clearance@ybl" in result["upi_ids"]


# ---------------------------------------------------------------------------
# Regex-first gating — no LLM call when not needed
# ---------------------------------------------------------------------------

def test_regex_first_gating_no_llm_call(monkeypatch):
    """Message with no indicator candidates + no classification hints -> no LLM call."""
    monkeypatch.setenv("LLM_BASE_URL", "http://fake")
    monkeypatch.setenv("LLM_API_KEY", "fake")
    monkeypatch.setenv("LLM_MODEL", "fake-model")

    spy = MagicMock()
    spy.return_value = (MagicMock(), "fake-model")

    with patch("extractor._get_llm_client", spy):
        # Purely conversational — no UPI, phone, URL, account, or scam keywords
        result = extract("Haan ji, please say that again slowly, I could not hear you.")

    # _get_llm_client should NOT have been called
    spy.assert_not_called()
    assert result["source"] == "regex"


# ---------------------------------------------------------------------------
# detect_signals
# ---------------------------------------------------------------------------

def test_detect_signals_otp():
    sigs = detect_signals("Please share your OTP now")
    assert "otp_mention" in sigs


def test_detect_signals_remote_app():
    sigs = detect_signals("Install AnyDesk on your phone")
    assert "remote_app_mention" in sigs


def test_detect_signals_none():
    sigs = detect_signals("Transfer money to the account")
    assert sigs == []


def test_phone_digits_not_account(monkeypatch):
    _no_llm_env(monkeypatch)
    r = extract("Call us at +91-9812345670. Transfer to account 50200012345678")
    assert r["account_numbers"] == ["50200012345678"]
    assert "+91-9812345670" in r["phone_numbers"]
