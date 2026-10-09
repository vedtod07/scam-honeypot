# DEMO.md — 3-Minute Demo Video Script

## Scam Honeypot | ForgeHacks 2026

---

### 0:00 — The Problem (15 seconds)
> "Every minute a scammer spends on a fake victim is a minute they're NOT spending on a real one.
> And when real victims get scammed, the UPI IDs, phone numbers, and URLs used by the scammer are almost never captured in a usable form.
> Scam Honeypot solves both problems at once."

**Show:** The red SIMULATED DEMO banner in the app.

---

### 0:15 — Start Auto-Run (45 seconds)
> "I'm going to start a Digital Arrest scam simulation. Watch the left panel — that's our AI victim Ramesh, 62, retired, bad with phones."

**Action:**
1. Select "Digital Arrest" from the sidebar
2. Click "▶ Start" with Auto-run enabled
3. Point at the chat bubbles appearing turn-by-turn
4. Point at the **Time Wasted** ticker climbing
5. Point at the right panel — **Collected Intel** panel filling in:
   - UPI ID: `verify.rbi2026@okhdfc`
   - Phone: `+91-9812345670`
   - URL: `http://rbi-verify.example.com`
   - Account: `50200012345678`

> "Notice how Ramesh never gives any real data — he just asks confused follow-up questions that force the scammer to keep repeating their indicators."

---

### 1:00 — Safety Guardrail (30 seconds)
> "What if Ramesh accidentally tried to share something sensitive?"

**Show/explain:**
- The `guardrail.py` module intercepts any reply containing 6-digit OTP-like numbers, 12-digit Aadhaar-like numbers, or 16-digit card numbers
- Blocks them, retries, or redacts with [REDACTED]
- The "Leaks Blocked" counter in the sidebar shows this live

> "The guardrail runs on every single reply before it's shown — making this safe to demo publicly."

---

### 1:30 — The Report (30 seconds)
> "At the end of the run, we auto-generate a structured report."

**Show:**
- Scroll down to the generated report
- Point at: summary table, indicators bullet list, draft cybercrime complaint
- Highlight the draft complaint text targeted at **1930 / cybercrime.gov.in**
- Click **"Download report.md"**

> "A real investigator or platform could ingest this JSON/markdown directly — no manual transcription from a victim's memory."

---

### 2:00 — Evaluation Metrics (30 seconds)
> "We ran ground-truth tests across all 4 scam scripts."

**Show:**
- The eval table in README.md or run `python eval.py` output
- UPI recall, phone recall, URL recall: 1.0 across all scripts (regex catches everything planted in the scripts)

> "We're being honest: this measures extraction correctness against our own synthetic scripts. Real-world performance needs adversarial testing. But the pipeline is solid."

---

### 2:30 — Impact Close (30 seconds)
> "Every minute here is a minute NOT spent on a real victim. And every indicator we capture — a UPI ID, a fake RBI phone number, a phishing URL — goes into a structured report ready for 1930."

**Show:** Final indicator panel with all 4 indicators for digital_arrest.

> "This is Scam Honeypot — an AI that fights back."

---

*Total: ~3 minutes*
