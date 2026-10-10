# Scam Honeypot — ForgeHacks 2026 Demo Script (2–3 min)

**Track 05: AI + Cybersecurity**

Total runtime target: ~2:30. Timestamps are approximate — practice once with the app warmed up.

---

## Before you record

1. **Warm up the model** — run one conversation first. The first LLM call after idle has a ~20s cold start.
2. **Never show your API key** — no terminals, no `.env`, no Featherless dashboard on screen.
3. Record the browser tab only, 1920×1080, with your mic.
4. The live run takes ~5–10 min; you'll **narrate over it and edit out the dead air** (or pre-run, then screen-record the finished conversation with the "Replay cached demo" mode).
5. Plan B if the API flakes: **Offline simulator** mode — instant, no API calls.

---

## 0:00–0:20 — Hook & problem

**On screen:** Title slide or the app's landing page (red SIMULATED banner visible).

**Say:**
> "Every day in India, thousands of people — most of them elderly — lose their life savings to phone scams: fake police arrests, KYC fraud, courier threats. In 2024 alone, Indians lost over ₹11,000 crore to cyber fraud. The scammers win because they're fast, automated, and relentless. What if we could fight back — with AI on our side?"

---

## 0:20–0:55 — Setup

**On screen:** Sidebar. Point at each control as you mention it.

**Say:**
> "Meet Scam Honeypot — a defensive AI tool that wastes scammers' time and harvests their payment details for law enforcement. Here's the idea: instead of hanging up, we put a decoy on the line — an AI persona, Ramesh Gupta, a 62-year-old retired government employee. Ramesh sounds confused and scared, so the scammer stays on the line... while the system quietly extracts every fraud indicator the scammer reveals."

**Do:**
- Pick **Digital Arrest** from the Scam Script dropdown.
- Point out Mode is **Live (LLM)** — "real AI agents talking to each other, powered by Qwen2.5-72B through Featherless."
- Point at the red banner: **"This is a simulated demo. No real scammer, no real data — safety first."**
- Click **▶ Start**.

---

## 0:55–1:40 — The live conversation

**On screen:** Conversation bubbles appear (🦹 scammer / 👴 persona), Time Wasted ticker running.

**Say (as the first messages land):**
> "The scammer agent opens with a classic digital-arrest script — 'courier intercepted in your name, five hundred grams of illegal substances.' Ramesh doesn't accuse or hang up — he stalls. Every reply ends with a confused question that makes the scammer repeat themselves, because repetition is exactly what we want: the more the scammer talks, the more evidence they leave behind."

**Say (mid-run, as more turns land):**
> "And here's the critical part: Ramesh can only ever reveal fake 'canary' data — nothing real. A guardrail layer checks every single reply before it's sent. If the model ever tries to leak a real value, the reply is blocked and rewritten. The Leaks Blocked counter stays at zero — by design."

**Say (as scammer escalates — link, UPI ID, account number):**
> "Watch what happens when the scammer gets impatient — he escalates to the actual money step: a fake RBI verification link... a UPI ID... a bank account number. Every one of these is being captured live by the extractor."

---

## 1:40–2:10 — The payoff: intel & report

**On screen:** Scroll to **Collected Intel** panel, then **Generated Report**.

**Say:**
> "When the call finally ends, the payoff appears: the scam type, the impersonated identity, the UPI ID, the phone number, the phishing URL, the bank account — every indicator the scammer burned time revealing. And it's not just a list — the system generates a full report: a summary of the interaction, the scam stages it observed — impersonation, fear hook, isolation, urgency, extraction — and a draft complaint, pre-formatted for the Cybercrime Helpline 1930."

**Do:**
- Point at **Scam Script Stages Observed**.
- Click **⬇ Download report.md** — "one click, and the victim has an evidence packet ready to file."

---

## 2:10–2:30 — How it works + outro

**On screen:** Keep the report visible; optionally a simple architecture diagram.

**Say:**
> "Under the hood: two LLM agents — a scammer simulator and a decoy persona — a guardrail that enforces the canary rules, an extractor that pulls indicators out of raw chat, and a Streamlit dashboard on top. Everything is configurable — four scam scripts, live or offline modes. Scam Honeypot flips the economics of fraud: the scammer's biggest advantage is time, and now their time is being stolen by a machine that never gets tired, never gets scared, and files the evidence for free. Thank you."

---

## Editing checklist

- Cut all LLM wait time between turns; keep the flow tight.
- Keep the red SIMULATED banner visible the whole time — it's the ethics story.
- End frame: the report + "Download report.md" button (or your team name/title card).
- Export 1080p, H.264, ≤3 min per ForgeHacks spec.
