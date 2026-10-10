"""
extractor.py — Scam Honeypot Phase 1
Extracts scam indicators (UPI IDs, phone numbers, URLs, account numbers,
claimed identity, scam type) from a scammer message using regex and
optionally an LLM (OpenAI-compatible, gated by env vars).
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_EMAIL_DOMAINS = {
    "gmail", "yahoo", "outlook", "hotmail", "icloud",
    "proton", "protonmail", "rediffmail", "zoho", "ymail",
}

KNOWN_UPI_HANDLES = {
    "okhdfcbank", "oksbi", "okaxis", "okicici",
    "paytm", "ybl", "ibl", "barodampay", "upi", "axl",
    "okbank",
}

SCAM_TYPES = ("digital_arrest", "kyc", "courier", "upi_collect", "unknown")

# Keyword context window for account numbers
_ACCT_CONTEXT_RE = re.compile(
    r"(?:account|a/c|ifsc|transfer).{0,40}\b(\d{9,18})\b"
    r"|\b(\d{9,18})\b.{0,40}(?:account|a/c|ifsc|transfer)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

def _extract_upi_ids(text: str) -> list[str]:
    """Extract UPI IDs, filtering out common email domains."""
    pattern = re.compile(r"\b([a-zA-Z0-9.\-_]{2,}@([a-zA-Z]{2,}))\b")
    results = []
    for match in pattern.finditer(text):
        full = match.group(1)
        domain = match.group(2).lower()
        handle = full.split("@")[0].lower()
        # Discard if it looks like a well-known email domain
        if domain in KNOWN_EMAIL_DOMAINS:
            continue
        # Prefer known UPI handles or those containing 'bank'/'pay'
        is_upi_domain = domain in KNOWN_UPI_HANDLES or any(
            kw in domain for kw in ("bank", "pay", "upi")
        )
        has_dot_domain = "." in domain  # emails usually have dotted domains
        if is_upi_domain or not has_dot_domain:
            results.append(full)
    return list(dict.fromkeys(results))  # dedup, preserve order


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return f"+91-{digits}"


def _extract_phones(text: str) -> list[str]:
    pattern = re.compile(r"(?:(?:\+91|0)[ \-]?)?([6-9]\d{9})\b")
    results = []
    for m in pattern.finditer(text):
        results.append(_normalize_phone(m.group(0)))
    return list(dict.fromkeys(results))


def _extract_urls(text: str) -> list[str]:
    pattern = re.compile(r"https?://\S+")
    return list(dict.fromkeys(pattern.findall(text)))


def _extract_accounts(text: str) -> list[str]:
    """Extract account-like numbers (9-18 digits) only near account keywords."""
    results = []
    # Mask phone numbers so their digits are not mistaken for account numbers
    text = re.sub(r"(?<!\d)(?:(?:\+91|0)[ \-]?)?[6-9]\d{9}(?!\d)", " ", text)
    for m in _ACCT_CONTEXT_RE.finditer(text):
        val = m.group(1) or m.group(2)
        if val:
            results.append(val)
    return list(dict.fromkeys(results))


def _classify_scam(text: str) -> str:
    tl = text.lower()
    if any(kw in tl for kw in ("digital arrest", "cyber cell", "ndps", "digitally arrested")):
        return "digital_arrest"
    if any(kw in tl for kw in ("kyc", "know your customer", "anydesk", "teamviewer")):
        return "kyc"
    if any(kw in tl for kw in ("fedex", "courier", "parcel", "customs", "clearance fee")):
        return "courier"
    if any(kw in tl for kw in ("upi collect", "collect request", "refund", "bank refund")):
        return "upi_collect"
    return "unknown"


def _regex_extract(text: str) -> dict:
    return {
        "upi_ids": _extract_upi_ids(text),
        "phone_numbers": _extract_phones(text),
        "urls": _extract_urls(text),
        "account_numbers": _extract_accounts(text),
        "claimed_identity": None,
        "scam_type": _classify_scam(text),
        "confidence": 0.6,
        "source": "regex",
    }


# ---------------------------------------------------------------------------
# Signal detection (OTP / remote-access app mentions)
# ---------------------------------------------------------------------------

_OTP_RE = re.compile(r"(?i)\b(otp|one.?time.?password|verification code)\b")
_REMOTE_RE = re.compile(r"(?i)\b(anydesk|teamviewer|rustdesk|quicksupport)\b")


def detect_signals(text: str) -> list[str]:
    """Return list of human-readable signal strings found in text."""
    signals = []
    if _OTP_RE.search(text):
        signals.append("otp_mention")
    if _REMOTE_RE.search(text):
        signals.append("remote_app_mention")
    return signals


# ---------------------------------------------------------------------------
# LLM helpers (graceful degradation)
# ---------------------------------------------------------------------------

def _get_llm_client():
    """Return an OpenAI client if env vars are present, else None."""
    base_url = os.environ.get("LLM_BASE_URL")
    api_key = os.environ.get("LLM_API_KEY")
    if not base_url or not api_key:
        return None, None
    try:
        from openai import OpenAI  # noqa: PLC0415
        client = OpenAI(base_url=base_url, api_key=api_key)
        return client, os.environ.get("LLM_MODEL", "gpt-4o-mini")
    except Exception as exc:
        logger.warning("Could not create LLM client: %s", exc)
        return None, None


_LLM_SYSTEM = """You are an expert scam-indicator extractor. Given a scammer's message, extract:
- upi_ids: list of UPI IDs (format: handle@provider)
- phone_numbers: list of Indian phone numbers normalised to "+91-XXXXXXXXXX"
- urls: list of URLs
- account_numbers: list of 9-18-digit account numbers
- claimed_identity: string, or null
- scam_type: one of "digital_arrest", "kyc", "courier", "upi_collect", "unknown"
- confidence: float 0-1

Respond with ONLY a valid JSON object matching exactly this schema. No prose, no markdown.

Example 1:
Input: "Inspector Rao here. Transfer 2L to 50200012345678 via verify.rbi2026@okhdfc"
Output: {"upi_ids":["verify.rbi2026@okhdfc"],"phone_numbers":[],"urls":[],"account_numbers":["50200012345678"],"claimed_identity":"Inspector Rao","scam_type":"digital_arrest","confidence":0.95}

Example 2:
Input: "Pay FedEx fee via fedex.clearance@ybl or visit http://fedex-clearance.example.com/pay, call +91-9765432109"
Output: {"upi_ids":["fedex.clearance@ybl"],"phone_numbers":["+91-9765432109"],"urls":["http://fedex-clearance.example.com/pay"],"account_numbers":[],"claimed_identity":null,"scam_type":"courier","confidence":0.9}
"""


def _parse_llm_json(raw: str) -> dict | None:
    """Defensively parse JSON from LLM response (handles code fences, trailing prose)."""
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
    # Slice first { to last }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        return None
    candidate = cleaned[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _llm_extract(text: str, client, model: str) -> dict | None:
    """Call LLM to extract indicators; retry once on JSON parse failure."""
    messages = [
        {"role": "system", "content": _LLM_SYSTEM},
        {"role": "user", "content": f"Extract indicators from:\n{text}"},
    ]
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model, messages=messages, temperature=0, max_tokens=400
            )
            raw = response.choices[0].message.content or ""
            parsed = _parse_llm_json(raw)
            if parsed and _validate_schema(parsed):
                return parsed
            logger.debug("LLM parse attempt %d failed, raw=%r", attempt + 1, raw[:200])
        except Exception as exc:
            logger.warning("LLM call attempt %d failed: %s", attempt + 1, exc)
    return None


def _validate_schema(d: dict) -> bool:
    required = {"upi_ids", "phone_numbers", "urls", "account_numbers", "scam_type"}
    return required.issubset(d.keys())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract(text: str) -> dict:
    """Extract scam indicators from a message. Returns structured dict."""
    regex_result = _regex_extract(text)

    # Regex-first gating: only call LLM when there are actual indicator candidates.
    # Classification-only (no candidates) is not worth a credit spend.
    has_candidates = any([
        regex_result["upi_ids"],
        regex_result["phone_numbers"],
        regex_result["urls"],
        regex_result["account_numbers"],
    ])
    should_call_llm = has_candidates

    if not should_call_llm:
        return regex_result

    client, model = _get_llm_client()
    if client is None:
        return regex_result

    llm_result = _llm_extract(text, client, model)
    if llm_result is None:
        return regex_result

    # Merge: union, dedup; prefer LLM for identity/type
    merged = {
        "upi_ids": list(dict.fromkeys(regex_result["upi_ids"] + llm_result.get("upi_ids", []))),
        "phone_numbers": list(dict.fromkeys(regex_result["phone_numbers"] + llm_result.get("phone_numbers", []))),
        "urls": list(dict.fromkeys(regex_result["urls"] + llm_result.get("urls", []))),
        "account_numbers": list(dict.fromkeys(regex_result["account_numbers"] + llm_result.get("account_numbers", []))),
        "claimed_identity": llm_result.get("claimed_identity") or regex_result.get("claimed_identity"),
        "scam_type": (
            llm_result.get("scam_type", "unknown")
            if llm_result.get("scam_type", "unknown") != "unknown"
            else regex_result["scam_type"]
        ),
        "confidence": max(regex_result["confidence"], llm_result.get("confidence", 0)),
        "source": "llm+regex",
    }
    return merged


def merge_indicators(acc: dict, new: dict) -> dict:
    """Merge new indicators into accumulator. Lists are unioned and deduped."""
    if not acc:
        return {
            "upi_ids": [],
            "phone_numbers": [],
            "urls": [],
            "account_numbers": [],
            "claimed_identity": None,
            "scam_type": "unknown",
        }
    result = dict(acc)
    for field in ("upi_ids", "phone_numbers", "urls", "account_numbers"):
        existing = result.get(field, [])
        incoming = new.get(field, [])
        result[field] = list(dict.fromkeys(existing + incoming))
    # claimed_identity: keep existing unless new is non-null
    if new.get("claimed_identity"):
        result["claimed_identity"] = new["claimed_identity"]
    # scam_type: keep existing unless new is non-null and not 'unknown'
    if new.get("scam_type") and new["scam_type"] != "unknown":
        result["scam_type"] = new["scam_type"]
    return result
