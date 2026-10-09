# DEVPOST.md — Submission Checklist

## Scam Honeypot | ForgeHacks 2026

---

### Tagline
> An AI "victim" that wastes scammers' time and extracts structured intelligence for India's cybercrime authorities.

---

### Description (copy to Devpost)

**What it does:**
Scam Honeypot deploys an AI persona (Ramesh Gupta, 62, retired, anxious) that engages a simulated scammer in conversation. The persona stalls, asks confused questions, and never completes a payment — while a background extractor (regex + optional LLM) captures every UPI ID, phone number, URL, and account number the scammer reveals. At the end, a structured report with a draft complaint for India's cybercrime helpline (1930 / cybercrime.gov.in) is generated.

**How we built it:**
- Python 3.11+ backend with two LLM roles (persona + scammer) via OpenAI-compatible API
- Hardened regex extractor (handles UPI vs email disambiguation, phone normalization, account context matching)
- Guardrail layer that blocks any sensitive-looking data from the persona's replies
- Streamlit dashboard with Live (LLM) and Replay (offline cache) modes
- Offline test suite: 26 tests, all green, no API key required

**Challenges:**
- UPI IDs and email addresses share the same `handle@domain` format — required careful domain denylist + UPI allowlist filtering
- Two LLMs can drift into circular loops — solved with a repetition circuit breaker (difflib.SequenceMatcher > 0.8)
- Python 3.14 is strict about inline regex flags in alternations — fixed by using compile-time `re.IGNORECASE`

**Accomplishments:**
- 26/26 tests green, all offline
- Replay mode: full demo experience with zero API calls (judges can always see it working)
- All 4 ground-truth indicators extracted at 1.0 recall from each scam script

**What we learned:**
- Regex-first gating dramatically reduces LLM cost without sacrificing accuracy
- A good persona prompt is the heart of the product — Ramesh's confusion is what makes the scammer keep repeating indicators

**What's next:**
- Adversarial testing with more evasive scammer scripts
- Hindi/Hinglish persona mode
- Integration with real reporting platforms (requires legal/compliance review)

---

### Built With
- Python 3.11+
- Streamlit
- OpenAI-compatible client (Featherless AI / OpenAI)
- pytest
- python-dotenv

---

### Checklist
- [ ] Live demo link: *(fill after Streamlit Cloud deploy)*
- [ ] Demo video link: *(fill after recording)*
- [ ] GitHub repo: https://github.com/vedtod07/scam-honeypot
- [ ] All team members registered on Devpost
- [ ] Submitted ≥ 2 hours before Oct 10 12:00 PM ET deadline
- [ ] Ethics section in README ✅
- [ ] AI-use disclosure in README ✅
- [ ] SIMULATED DEMO badge visible in app at all times ✅
- [ ] Report ends with simulation disclaimer ✅

---

### Track
ForgeHacks 2026 · Track 05: AI + Cybersecurity
