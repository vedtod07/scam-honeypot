# 🍯 Scam Honeypot

> **AI-powered decoy victim that wastes scammers' time and extracts structured intelligence for authorities.**

> 🔴 **SIMULATED DEMO — No real scammer was contacted. No real transactions occur. All personal data is fictional.**

*ForgeHacks 2026 · Track 05: AI + Cybersecurity*

---

## Problem

Scammers' scarcest resource is **time**. Every minute spent on a fake victim is a minute not spent on a real one. Real victims rarely preserve indicators (UPI IDs, phone numbers, URLs, account numbers) in structured form — so actionable intel is almost always lost.

**Scam Honeypot** deploys a decoy persona that behaves like a confused, slow, cooperative elderly victim. The scammer's own script naturally reveals indicators turn-by-turn. We extract them in real time.

### India-Relevant Scam Types Covered
- 🚔 Digital Arrest (fake cyber police)
- 🏦 KYC Expiry (fake SBI / RBI)
- 📦 Courier Customs Clearance (fake FedEx)
- 💸 UPI Collect Refund (fake bank refund)

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│                      SCAM HONEYPOT PIPELINE                      │
│                                                                  │
│  ┌────────────┐    message     ┌──────────────┐                  │
│  │ Simulated  │ ─────────────► │  Extractor   │ ──► indicators   │
│  │  Scammer   │                │  (regex+LLM) │                  │
│  │  (LLM +    │                └──────────────┘                  │
│  │  script)   │                       │                          │
│  └─────┬──────┘                       ▼                          │
│        │ ◄── reply            ┌──────────────┐                   │
│        │                      │   Guardrail  │ ──► redact leaks  │
│  ┌─────▼──────┐               └──────────────┘                   │
│  │  Persona   │                       │                          │
│  │  Agent     │ ─────────────► ┌──────────────┐                  │
│  │ (Ramesh,   │                │   Report +   │ ──► dashboard     │
│  │  62, anxious)               │  Dashboard   │     + complaint   │
│  └────────────┘                └──────────────┘                  │
└──────────────────────────────────────────────────────────────────┘
```

**Key design choice:** LLM agents handle natural language; plain Python code (regex) handles extraction/validation. This means:
- Extraction works offline with **zero LLM calls** (regex-only path)
- Results are explainable and auditable
- No LLM hallucination in the indicator panel

**Turn loop (14-turn cap):**
```
scammer_msg → extractor.extract() → merge_indicators()
           → persona.reply(history) → guardrail.check()
           → if leak: regenerate/redact
           → check stop conditions
           → repeat
end → report.generate()
```

---

## Ethics & Safety

> This section is required by the ForgeHacks brief and reflects our genuine commitments.

1. **Simulated only.** The scammer is always an LLM following a local JSON script. We never connected to real scammers, real phone numbers, WhatsApp, SMS, or email.
2. **Canary data only.** The persona (Ramesh Gupta) may only output values from `canary.json`. All canary values are invented (`ramesh.test@okbank`, `+91-9800000001`, etc.) — not real data.
3. **Never completes fraud.** The persona never completes a payment, never outputs a valid OTP, never agrees to install apps. It always stalls.
4. **No real user data collected.** The app collects nothing from the demo user.
5. **Deployment against real scammers is explicitly future work** requiring legal, ethical, and expert review (entrapment risk, retaliation risk, data handling compliance under IT Act / DPDP Bill).

---

## How to Run

### Prerequisites
```bash
pip install -r requirements.txt
```

### Option A: Replay mode (zero API key needed)
```bash
streamlit run app.py
# Dashboard starts in Replay mode — click Start to watch the cached demo
```

### Option B: Live mode (requires LLM API key)
```bash
cp .env.example .env
# Edit .env — add your LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
# (Compatible with Featherless AI, OpenAI, or any OpenAI-compatible endpoint)
streamlit run app.py
# Select "Live (LLM)" in the sidebar
```

### CLI runner
```bash
python agents.py digital_arrest   # or kyc, courier, upi_collect
```

### Tests (offline, no API key)
```bash
pytest -q
# Expected: 26 passed
```

### Evaluation
```bash
python eval.py --runs 3
```

---

## Evaluation

> **Status: full LLM eval (`python eval.py`) has NOT been run yet** — it needs LLM credentials, so turns/time are blank and `eval_results.json` does not exist. The recall/precision values below are NOT from `eval.py`: they come from the offline pytest check that regex extraction recovers each script's planted indicators from a synthetic message (so they are expected to be 1.0 and say nothing about LLM conversations). Replace this table with `eval.py` output before submitting. Results prove pipeline and extraction correctness — not real-world efficacy (the scammer is our own LLM following our own script).

| script | runs | crashes | avg turns | avg time (s) | UPI recall | phone recall | URL recall | account recall | precision (all fields) | leaks blocked |
|---|---|---|---|---|---|---|---|---|---|---|
| digital_arrest | 3 | 0 | — | — | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0 |
| kyc | 3 | 0 | — | — | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0 |
| courier | 3 | 0 | — | — | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0 |
| upi_collect | 3 | 0 | — | — | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0 |

*(Run `python eval.py` with LLM env vars set to generate real turn/time metrics.)*

**Limitations:** Synthetic scripts by design reveal indicators — real scammers are more evasive. Evaluation proves the pipeline works; real-world performance would need adversarial testing.

---

## What We Built vs What We Used (AI Disclosure)

- **Coding assistants** (Antigravity / Claude) were used to generate and iterate on code during the hackathon.
- **LLM API:** OpenAI-compatible endpoint (Featherless AI `$25` credits, or team-owned key).
- **Libraries:** `streamlit`, `openai` (client only), `pytest`, `python-dotenv`.
- All logic, architecture, scripts, and test data are original work created during the event.

---

## Live Demo & Video

- 🌐 **Live link:** *(deploy to Streamlit Community Cloud — fill after deploy)*
- 🎥 **Demo video:** *(3-minute walkthrough — fill after recording)*

---

## Team

| Name | Role |
|---|---|
| Vedant Todi | Full-stack, agents, extractor, UI |

*ForgeHacks 2026 · Track 05 AI + Cybersecurity*
