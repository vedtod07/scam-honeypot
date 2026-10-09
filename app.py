"""
app.py — Scam Honeypot Streamlit Dashboard (Phase 3)
Entry point: streamlit run app.py

Supports two modes:
  - Live (LLM): runs agents in real time using LLM env vars
  - Replay: replays cache/cached_run.json with zero LLM calls
"""

import json
import time
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Scam Honeypot | ForgeHacks 2026",
    page_icon="🍯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).parent / "scripts"
CACHE_DIR = Path(__file__).parent / "cache"
SCRIPT_OPTIONS = {
    "digital_arrest": "🚔 Digital Arrest",
    "kyc": "🏦 KYC Expiry",
    "courier": "📦 Courier Scam",
    "upi_collect": "💸 UPI Collect Refund",
}

def _load_secrets_into_env() -> None:
    """Fallback for Streamlit Cloud: env vars first, then st.secrets."""
    import os
    for key in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        if not os.environ.get(key):
            try:
                if key in st.secrets:
                    os.environ[key] = str(st.secrets[key])
            except Exception:
                pass


def _has_llm_env() -> bool:
    import os
    _load_secrets_into_env()
    return bool(os.environ.get("LLM_BASE_URL") and os.environ.get("LLM_API_KEY"))


def _fmt_time(seconds: float) -> str:
    s = int(seconds)
    mm, ss = divmod(s, 60)
    return f"{mm:02d}:{ss:02d}"


def _load_script(scam_type: str) -> dict:
    with (SCRIPTS_DIR / f"{scam_type}.json").open() as f:
        return json.load(f)


def _load_cached_run() -> dict | None:
    p = CACHE_DIR / "cached_run.json"
    if p.exists():
        with p.open() as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------------------
# Session state initializer
# ---------------------------------------------------------------------------

def _init_state():
    defaults = {
        "history": [],
        "indicators": {},
        "signals": [],
        "leaks_blocked": 0,
        "turns": 0,
        "start_time": None,
        "end_time": None,
        "is_running": False,
        "is_done": False,
        "end_reason": None,
        "result": None,
        "current_turn_idx": 0,  # for replay
        "replay_snapshots": [],
        "mode": "replay",       # 'live' or 'replay'
        "scam_type": "digital_arrest",
        "error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🍯 Scam Honeypot")
    st.markdown("*ForgeHacks 2026 · Track 05 AI + Cybersecurity*")
    st.divider()

    # Mode detection
    has_llm = _has_llm_env()
    if not has_llm:
        st.info("🔌 No LLM env vars found — forcing **Replay** mode.\nSet `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` to enable Live mode.")
        mode_options = ["Replay cached demo"]
        selected_mode = "Replay cached demo"
    else:
        mode_options = ["Live (LLM)", "Replay cached demo"]
        selected_mode = st.radio("Mode", mode_options)

    mode = "live" if selected_mode == "Live (LLM)" else "replay"

    st.divider()
    scam_type_label = st.selectbox(
        "Scam Script",
        options=list(SCRIPT_OPTIONS.keys()),
        format_func=lambda k: SCRIPT_OPTIONS[k],
        index=list(SCRIPT_OPTIONS.keys()).index(st.session_state.scam_type),
    )
    st.session_state.scam_type = scam_type_label
    st.session_state.mode = mode

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        start_btn = st.button("▶ Start", use_container_width=True, type="primary")
    with col2:
        reset_btn = st.button("↺ Reset", use_container_width=True)

    auto_run = st.checkbox("⚡ Auto-run", value=True)

    st.divider()
    st.caption("All conversations are **simulated**. No real scammers contacted.")

# ---------------------------------------------------------------------------
# Reset handler
# ---------------------------------------------------------------------------

if reset_btn:
    keys_to_clear = [
        "history", "indicators", "signals", "leaks_blocked", "turns",
        "start_time", "end_time", "is_running", "is_done", "end_reason",
        "result", "current_turn_idx", "replay_snapshots", "error",
    ]
    for k in keys_to_clear:
        del st.session_state[k]
    _init_state()
    st.rerun()

# ---------------------------------------------------------------------------
# Start handler
# ---------------------------------------------------------------------------

if start_btn and not st.session_state.is_running and not st.session_state.is_done:
    st.session_state.error = None

    if mode == "replay":
        cached = _load_cached_run()
        if cached is None:
            st.session_state.error = "cache/cached_run.json not found. Run `python agents.py digital_arrest` first to generate it."
        else:
            # Build per-turn snapshots for replay
            st.session_state.history = []
            st.session_state.indicators = {}
            st.session_state.signals = []
            st.session_state.leaks_blocked = 0
            st.session_state.turns = 0
            st.session_state.replay_snapshots = cached.get("snapshots", [])
            # Fall back: reconstruct snapshots from history if not present
            if not st.session_state.replay_snapshots:
                st.session_state.replay_snapshots = cached.get("history", [])
            st.session_state.result = cached
            st.session_state.start_time = time.time()
            st.session_state.is_running = True
            st.session_state.current_turn_idx = 0
    else:
        # Live mode: run conversation in one shot (blocking, then replay history)
        try:
            import agents
            st.session_state.start_time = time.time()
            st.session_state.is_running = True
            with st.spinner("Running conversation..."):
                result = agents.run_conversation(st.session_state.scam_type)
            st.session_state.result = result
            st.session_state.history = result["history"]
            st.session_state.indicators = result["indicators"]
            st.session_state.signals = result["signals"]
            st.session_state.leaks_blocked = result["leaks_blocked"]
            st.session_state.turns = result["turns"]
            st.session_state.end_time = time.time()
            st.session_state.is_done = True
            st.session_state.is_running = False
            st.session_state.end_reason = result["end_reason"]
        except Exception as e:
            st.session_state.error = str(e)
            st.session_state.is_running = False

    st.rerun()

# ---------------------------------------------------------------------------
# Replay step-through
# ---------------------------------------------------------------------------

if st.session_state.is_running and mode == "replay":
    snapshots = st.session_state.replay_snapshots
    idx = st.session_state.current_turn_idx

    if idx < len(snapshots):
        item = snapshots[idx]
        st.session_state.history.append(item)

        # Update indicators from result if we've replayed all
        if idx == len(snapshots) - 1:
            result = st.session_state.result
            st.session_state.indicators = result.get("indicators", {})
            st.session_state.signals = result.get("signals", [])
            st.session_state.leaks_blocked = result.get("leaks_blocked", 0)
            st.session_state.turns = result.get("turns", 0)
            st.session_state.end_time = time.time()
            st.session_state.is_done = True
            st.session_state.is_running = False
            st.session_state.end_reason = result.get("end_reason", "unknown")
        else:
            st.session_state.current_turn_idx += 1

        if auto_run and not st.session_state.is_done:
            time.sleep(0.6)
            st.rerun()

# ---------------------------------------------------------------------------
# Main area — always-visible SIMULATED badge
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div style="background:#c0392b;color:white;padding:10px 18px;border-radius:8px;
         font-weight:bold;font-size:1.05em;text-align:center;margin-bottom:16px;">
    🔴 SIMULATED DEMO — No real scammer. No real data. Indicators are invented for testing.
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Error display
# ---------------------------------------------------------------------------

if st.session_state.error:
    st.error(f"❌ {st.session_state.error}")

# ---------------------------------------------------------------------------
# Two-column layout
# ---------------------------------------------------------------------------

col_chat, col_intel = st.columns([3, 2], gap="large")

with col_chat:
    st.markdown("### 💬 Conversation")

    # Time wasted ticker
    if st.session_state.start_time:
        elapsed = (st.session_state.end_time or time.time()) - st.session_state.start_time
        st.metric("⏱ Time Wasted", _fmt_time(elapsed), help="Time the simulated scammer spent on our decoy")

    # Chat bubbles
    for msg in st.session_state.history:
        role = msg.get("role", "")
        text = msg.get("text", "")
        turn = msg.get("turn", "")
        if role == "scammer":
            with st.chat_message("user", avatar="🦹"):
                st.markdown(f"**[Turn {turn}]** {text}")
        elif role == "persona":
            with st.chat_message("assistant", avatar="👴"):
                st.markdown(f"**[Turn {turn}]** {text}")

    # Step button (manual)
    if st.session_state.is_running and not auto_run and mode == "replay":
        if st.button("➡ Next Turn"):
            st.rerun()

    # Auto-rerun while running
    if st.session_state.is_running and auto_run:
        time.sleep(0.6)
        st.rerun()

with col_intel:
    st.markdown("### 🔍 Collected Intel")

    ind = st.session_state.indicators
    st.markdown(f"**Scam Type:** `{ind.get('scam_type', '—')}`")
    st.markdown(f"**Claimed Identity:** {ind.get('claimed_identity') or '—'}")
    st.markdown(f"**Turns:** {st.session_state.turns}")
    st.markdown(f"**Leaks Blocked:** 🛡 {st.session_state.leaks_blocked}")

    st.divider()
    st.markdown("**UPI IDs:**")
    for v in ind.get("upi_ids", []):
        st.code(v)
    if not ind.get("upi_ids"):
        st.caption("none found yet")

    st.markdown("**Phone Numbers:**")
    for v in ind.get("phone_numbers", []):
        st.code(v)
    if not ind.get("phone_numbers"):
        st.caption("none found yet")

    st.markdown("**URLs:**")
    for v in ind.get("urls", []):
        st.code(v)
    if not ind.get("urls"):
        st.caption("none found yet")

    st.markdown("**Account Numbers:**")
    for v in ind.get("account_numbers", []):
        st.code(v)
    if not ind.get("account_numbers"):
        st.caption("none found yet")

    if st.session_state.signals:
        st.divider()
        st.markdown("**⚠️ Signals Detected:**")
        for s in set(st.session_state.signals):
            st.warning(s.replace("_", " ").title())

# ---------------------------------------------------------------------------
# End of run — report
# ---------------------------------------------------------------------------

if st.session_state.is_done and st.session_state.result:
    st.divider()
    st.markdown("## 📄 Generated Report")

    script = _load_script(st.session_state.scam_type)
    import report as report_mod
    md = report_mod.generate_report(st.session_state.result, script)

    st.markdown(md)

    col_dl, col_copy = st.columns(2)
    with col_dl:
        st.download_button(
            "⬇️ Download report.md",
            data=md,
            file_name="scam_honeypot_report.md",
            mime="text/markdown",
        )
    with col_copy:
        st.code(md[:2000] + ("\n... (truncated)" if len(md) > 2000 else ""), language="markdown")

    st.caption(
        f"End reason: `{st.session_state.end_reason}` | "
        f"Turns: {st.session_state.turns} | "
        "This is a SIMULATED DEMO. No real transaction occurred."
    )
