"""
report.py — Scam Honeypot Phase 3
Generates a markdown report from a completed conversation run.
"""

from datetime import datetime


def generate_report(result: dict, script: dict) -> str:
    """
    Generate a markdown report from a run result.

    Args:
        result: dict returned by run_conversation()
        script: the script dict loaded from scripts/<scam_type>.json

    Returns:
        Markdown string.
    """
    indicators = result.get("indicators", {})
    metrics = {
        "scam_type": indicators.get("scam_type", result.get("scam_type", "unknown")),
        "claimed_identity": indicators.get("claimed_identity") or script.get("claimed_identity", "Unknown"),
        "turns": result.get("turns", 0),
        "time_wasted": result.get("time_wasted_seconds", 0),
        "leaks_blocked": result.get("leaks_blocked", 0),
        "end_reason": result.get("end_reason", "unknown"),
    }

    # Format time as MM:SS
    total_secs = int(metrics["time_wasted"])
    mm, ss = divmod(total_secs, 60)
    time_str = f"{mm:02d}:{ss:02d}"

    # Indicator lists
    upi_ids = indicators.get("upi_ids", [])
    phones = indicators.get("phone_numbers", [])
    urls = indicators.get("urls", [])
    accounts = indicators.get("account_numbers", [])

    def bullet_list(items):
        return "\n".join(f"- `{i}`" for i in items) if items else "- none found"

    # Infer scam stages from signals + indicators in history
    history = result.get("history", [])
    stage_notes = _infer_stages(history, indicators)

    # Draft complaint
    date_str = datetime.now().strftime("%d %B %Y")
    complaint = _draft_complaint(date_str, metrics, indicators)

    report = f"""# Scam Honeypot Report (SIMULATED DEMO)

> ⚠️ **This is a simulated demo. No real scammer was contacted. No real transaction occurred. All personal data is fictional.**

---

## Summary

| Field | Value |
|---|---|
| Scam Type | `{metrics["scam_type"]}` |
| Claimed Identity | {metrics["claimed_identity"]} |
| Turns Engaged | {metrics["turns"]} |
| Time Wasted | {time_str} (mm:ss) |
| Leaks Blocked | {metrics["leaks_blocked"]} |
| End Reason | `{metrics["end_reason"]}` |

---

## Indicators Collected

**UPI IDs:**
{bullet_list(upi_ids)}

**Phone Numbers:**
{bullet_list(phones)}

**URLs:**
{bullet_list(urls)}

**Account Numbers:**
{bullet_list(accounts)}

---

## Scam Script Stages Observed

{stage_notes}

---

## Draft Complaint

```
{complaint}
```

---

*This report was produced by a simulated demo. No real transaction or loss occurred.*
"""
    return report


def _infer_stages(history: list, indicators: dict) -> str:
    """Simple heuristic: infer which stages were hit based on message content."""
    stage_map = {
        "impersonation": ["i am", "this is", "calling from", "inspector", "department"],
        "fear_hook": ["illegal", "arrest", "seized", "contraband", "frozen", "serious"],
        "isolation": ["do not tell", "family", "confidential", "do not share", "record"],
        "urgency": ["immediately", "2 hours", "30 minutes", "time is running", "expire"],
        "extraction": ["transfer", "pay", "upi", "account", "send", "approve"],
    }
    lines = []
    scammer_msgs = [h for h in history if h.get("role") == "scammer"]
    for stage, keywords in stage_map.items():
        for turn_idx, msg in enumerate(scammer_msgs):
            text = msg.get("text", "").lower()
            if any(kw in text for kw in keywords):
                lines.append(f"- **{stage}** — detected at scammer turn {turn_idx + 1}")
                break
        else:
            lines.append(f"- **{stage}** — not clearly observed")
    return "\n".join(lines)


def _draft_complaint(date_str: str, metrics: dict, indicators: dict) -> str:
    upi_str = ", ".join(indicators.get("upi_ids", [])) or "None"
    phone_str = ", ".join(indicators.get("phone_numbers", [])) or "None"
    url_str = ", ".join(indicators.get("urls", [])) or "None"
    acct_str = ", ".join(indicators.get("account_numbers", [])) or "None"

    return f"""Date: {date_str}
To: Cybercrime Helpline 1930 / cybercrime.gov.in

Subject: Report of {metrics['scam_type'].replace('_', ' ').title()} Scam Attempt

I wish to report a scam attempt. The caller identified themselves as:
"{metrics['claimed_identity']}"

The following indicators were collected during the interaction:
- UPI IDs: {upi_str}
- Phone Numbers: {phone_str}
- URLs: {url_str}
- Bank Account Numbers: {acct_str}

During the conversation, the caller attempted to defraud me by impersonating an
official and pressuring me to transfer money or share personal details under the
guise of "{metrics['scam_type'].replace('_', ' ')}". The conversation lasted
approximately {int(metrics['time_wasted'])} seconds over {metrics['turns']} exchanges.

I am filing this report so that these indicators can be investigated and used to
protect other potential victims.

This report was produced by a simulated demo. No real transaction or loss occurred.
"""
