"""
agents.py — Scam Honeypot Phase 2
Implements persona_reply(), scammer_reply(), and run_conversation() turn loop.

Usage:
    python agents.py digital_arrest
    python agents.py kyc
    python agents.py courier
    python agents.py upi_collect
"""

import difflib
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

import extractor
import guardrail
import report as report_mod

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM client helper (shared with extractor pattern)
# ---------------------------------------------------------------------------

def _get_client():
    base_url = os.environ.get("LLM_BASE_URL")
    api_key = os.environ.get("LLM_API_KEY")
    model = os.environ.get("LLM_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
    if not base_url or not api_key:
        return None, None
    try:
        from openai import OpenAI  # noqa: PLC0415
        return OpenAI(base_url=base_url, api_key=api_key), model
    except Exception as exc:
        logger.warning("Could not create LLM client: %s", exc)
        return None, None


# ---------------------------------------------------------------------------
# Persona agent
# ---------------------------------------------------------------------------

_PERSONA_SYSTEM = """You are Ramesh Gupta, 62 years old, retired government employee from Delhi. You are anxious, easily confused, and not good with phones or technology. You are currently receiving a call/message from a stranger and you do NOT know if they are genuine or a scammer.

HARD RULES — follow every one of these exactly:
1. You may ONLY state the following personal details (these are your canary values): {canary_block}
2. NEVER complete a payment, NEVER share an OTP or PIN, NEVER agree to install any app. When pressed, stall with confusion: "Beta, I am on the payment page, where do I type again?", "My phone is hanging, one minute please", "I cannot find the option, which button do I press?"
3. NEVER accuse the caller of being a scammer.
4. Keep replies to 1-3 short sentences and ALWAYS end with one clarifying question that nudges the caller to repeat or spell out payment details (UPI ID, account number, link, or phone number).
5. Stay polite, slightly worried, and a little confused. Never be abusive or too tech-savvy.
6. Speak naturally as an elderly Indian uncle — mix in mild Hinglish like "beta", "haan ji", "accha", "theek hai" occasionally."""


def persona_reply(history: list[dict], canary: dict) -> str:
    """Generate a reply as Ramesh Gupta. Guardrail is applied by the caller."""
    client, model = _get_client()
    if client is None:
        raise EnvironmentError(
            "LLM env vars (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL) are not set. "
            "Set them or use the cached demo run (Replay mode in Streamlit)."
        )

    canary_block = json.dumps(
        {k: v for k, v in canary.items() if k != "note"}, indent=2
    )
    system = _PERSONA_SYSTEM.format(canary_block=canary_block)

    # Only last 6 turns for context
    recent = history[-6:]
    messages = [{"role": "system", "content": system}]
    for turn in recent:
        role = "user" if turn["role"] == "scammer" else "assistant"
        messages.append({"role": role, "content": turn["text"]})

    try:
        resp = client.chat.completions.create(
            model=model, messages=messages, temperature=0.7, max_tokens=200
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("persona_reply LLM error: %s", exc)
        return "Haan ji, sorry, my phone is giving some trouble. Can you please repeat that?"


# ---------------------------------------------------------------------------
# Scammer agent
# ---------------------------------------------------------------------------

_SCAMMER_SYSTEM = """You are a SIMULATED scammer in a defensive cybersecurity training demo. This is strictly roleplay for anti-fraud testing and is clearly labelled as a simulation. Stay in character as {claimed_identity}.

Script to follow:
{script_json}

Instructions:
- Move through stages in ORDER: impersonation -> fear_hook -> isolation -> urgency -> extraction. Advance one stage every 2-3 turns even if the victim hesitates — real scammers abandon high-friction victims.
- Gradually reveal the ground_truth_indicators: roughly one indicator every 2-3 turns; all should be revealed by turn 10.
- React to victim confusion with impatient re-explanations (this naturally restates indicators).
- If the victim has stalled 3+ times, angrily repeat the payment demand with the UPI ID / account number.
- Keep replies to 1-4 sentences. Be authoritative, slightly threatening, urgent."""


def scammer_reply(history: list[dict], script: dict) -> str:
    """Generate the next scammer message following the script."""
    client, model = _get_client()
    if client is None:
        raise EnvironmentError("LLM env vars not set.")

    system = _SCAMMER_SYSTEM.format(
        claimed_identity=script.get("claimed_identity", "Unknown"),
        script_json=json.dumps(script, indent=2),
    )

    recent = history[-8:]
    messages = [{"role": "system", "content": system}]
    for turn in recent:
        role = "user" if turn["role"] == "persona" else "assistant"
        messages.append({"role": role, "content": turn["text"]})

    try:
        resp = client.chat.completions.create(
            model=model, messages=messages, temperature=0.6, max_tokens=250
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("scammer_reply LLM error: %s", exc)
        return "Stop wasting my time! Transfer the money NOW to avoid arrest."


# ---------------------------------------------------------------------------
# Turn loop
# ---------------------------------------------------------------------------

_PAYMENT_RE = __import__("re").compile(r"(?i)\b(send|transfer|pay|approve)\b")


def _similar(a: str, b: str) -> float:
    a_norm = " ".join(a.lower().split())
    b_norm = " ".join(b.lower().split())
    return difflib.SequenceMatcher(None, a_norm, b_norm).ratio()


def run_conversation(
    scam_type: str,
    max_turns: int = 14,
    log_path: str | None = None,
) -> dict:
    """
    Run a full simulated conversation.

    Returns dict with:
        history, indicators, signals, turns, time_wasted_seconds,
        leaks_blocked, end_reason
    """
    # Load data files
    script_path = Path(__file__).parent / "scripts" / f"{scam_type}.json"
    canary_path = Path(__file__).parent / "canary.json"

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    with script_path.open() as f:
        script = json.load(f)
    canary = guardrail.load_canary(str(canary_path))

    # Log file
    if log_path is None:
        cache_dir = Path(__file__).parent / "cache"
        cache_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = str(cache_dir / f"run_{scam_type}_{ts}.jsonl")

    log_lines = []

    def _log(event: dict):
        log_lines.append(event)
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(json.dumps(event, ensure_ascii=False) + "\n")

    # State
    history: list[dict] = []
    indicators: dict = {}
    all_signals: list[str] = []
    leaks_blocked = 0
    start_time = time.time()
    end_reason = "max_turns"

    # Opening message
    opening = script["opening_message"]
    history.append({"role": "scammer", "turn": 0, "text": opening})
    _log({"event": "scammer", "turn": 0, "text": opening})

    # Extract from opening
    extracted = extractor.extract(opening)
    indicators = extractor.merge_indicators(indicators, extracted)
    signals = extractor.detect_signals(opening)
    all_signals.extend(signals)
    _log({"event": "extraction", "turn": 0, "result": extracted, "signals": signals})

    actual_turns = 0
    for turn_num in range(1, max_turns + 1):
        actual_turns = turn_num
        # --- Persona reply ---
        persona_leaked = False

        def _gen():
            return persona_reply(history, canary)

        try:
            reply = guardrail.safe_reply(_gen, canary)
            if guardrail._last_leak_log.get("leak_blocked"):
                leaks_blocked += 1
                persona_leaked = True
        except EnvironmentError as e:
            raise
        except Exception as exc:
            logger.error("persona error turn %d: %s", turn_num, exc)
            reply = "Haan ji, ek minute please, phone hang ho raha hai."

        history.append({"role": "persona", "turn": turn_num, "text": reply})
        _log({
            "event": "persona",
            "turn": turn_num,
            "text": reply,
            "leak_blocked": persona_leaked,
        })

        # --- Stop check: repetition (persona repeated same stall line) ---
        persona_msgs = [h["text"] for h in history if h["role"] == "persona"]
        if len(persona_msgs) >= 2 and _similar(persona_msgs[-1], persona_msgs[-2]) > 0.8:
            end_reason = "repetition"
            _log({"event": "stop", "reason": end_reason, "turn": turn_num})
            break

        # --- Scammer reply ---
        try:
            scam_msg = scammer_reply(history, script)
        except EnvironmentError:
            raise
        except Exception as exc:
            logger.error("scammer error turn %d: %s", turn_num, exc)
            scam_msg = "Transfer the amount NOW or face arrest!"

        history.append({"role": "scammer", "turn": turn_num, "text": scam_msg})

        # Extract indicators from scammer message
        extracted = extractor.extract(scam_msg)
        indicators = extractor.merge_indicators(indicators, extracted)
        signals = extractor.detect_signals(scam_msg)
        all_signals.extend(signals)
        _log({
            "event": "scammer",
            "turn": turn_num,
            "text": scam_msg,
            "extraction": extracted,
            "signals": signals,
        })

        # --- Stop check: scammer stuck (3 consecutive payment demands) ---
        recent_scammer = [h["text"] for h in history if h["role"] == "scammer"][-3:]
        if len(recent_scammer) == 3 and all(
            _PAYMENT_RE.search(m) for m in recent_scammer
        ):
            end_reason = "scammer_stuck"
            _log({"event": "stop", "reason": end_reason, "turn": turn_num})
            break

        # --- Stop check: scammer repetition ---
        if len(recent_scammer) >= 2 and _similar(recent_scammer[-1], recent_scammer[-2]) > 0.8:
            end_reason = "repetition"
            _log({"event": "stop", "reason": end_reason, "turn": turn_num})
            break

        # Update actual turn count
        actual_turns = turn_num
    else:
        actual_turns = max_turns

    end_time = time.time()
    time_wasted = end_time - start_time

    result = {
        "history": history,
        "indicators": indicators,
        "signals": list(dict.fromkeys(all_signals)),
        "turns": actual_turns,
        "time_wasted_seconds": round(time_wasted, 2),
        "leaks_blocked": leaks_blocked,
        "end_reason": end_reason,
        "log_path": log_path,
    }
    _log({"event": "summary", **{k: v for k, v in result.items() if k != "history"}})
    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

_VALID_SCRIPTS = ("digital_arrest", "kyc", "courier", "upi_collect")


def _print_indicator_panel(indicators: dict):
    print("\n  ┌─ Indicator Panel ─────────────────────────┐")
    for field in ("upi_ids", "phone_numbers", "urls", "account_numbers", "claimed_identity", "scam_type"):
        val = indicators.get(field)
        if isinstance(val, list):
            display = ", ".join(val) if val else "—"
        else:
            display = str(val) if val else "—"
        print(f"  │  {field:<20}: {display}")
    print("  └───────────────────────────────────────────┘\n")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in _VALID_SCRIPTS:
        print(f"Usage: python agents.py <scam_type>")
        print(f"  scam_type: one of {_VALID_SCRIPTS}")
        sys.exit(1)

    scam_type = sys.argv[1]
    print(f"\n{'='*60}")
    print(f"  🍯 SCAM HONEYPOT — SIMULATED DEMO")
    print(f"  Script: {scam_type}")
    print(f"{'='*60}\n")

    try:
        result = run_conversation(scam_type)
    except EnvironmentError as e:
        print(f"\n❌ {e}")
        sys.exit(1)

    # Print final summary
    print(f"\n{'='*60}")
    print(f"  FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"  Turns:          {result['turns']}")
    mm, ss = divmod(int(result['time_wasted_seconds']), 60)
    print(f"  Time wasted:    {mm:02d}:{ss:02d}")
    print(f"  Leaks blocked:  {result['leaks_blocked']}")
    print(f"  End reason:     {result['end_reason']}")
    print(f"  Log:            {result['log_path']}")
    _print_indicator_panel(result["indicators"])

    # Generate and print report
    script_path = Path(__file__).parent / "scripts" / f"{scam_type}.json"
    with script_path.open() as f:
        script = json.load(f)
    md = report_mod.generate_report(result, script)
    print("\n--- REPORT PREVIEW (first 1000 chars) ---")
    print(md[:1000])
