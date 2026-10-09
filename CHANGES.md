# Modifications log

What changed after the Phase 1-4 build, and why. Everything stays simulated-only, canary-only.

## 1. Offline simulator (run everything without an LLM key)
- **New `offline.py`**: a deterministic, seeded stand-in for the persona and scammer.
  - The scammer walks the script's stages and reveals the planted indicators on a schedule.
  - The persona uses a pool of stall lines, and with ~20% probability "slips" with an OTP or card number, so the guardrail is exercised for real.
  - It is rule-based, not a language model. Results measure the pipeline, not model quality.
- `agents.run_conversation(..., offline=True, seed=N)`. `time_wasted_seconds` is **simulated** in this mode, and the result carries `simulated: True`.
- CLI: `python agents.py kyc --offline`.
- Streamlit: new sidebar mode **Offline simulator (no LLM)**. Replay stays the default with no key.

## 2. Evaluation (`eval.py`, rewritten)
- `python eval.py --runs 5 --offline` runs with no key. Without `--offline`, the live-LLM path is unchanged.
- Fields with no planted indicator show `n/a` instead of a misleading 1.0.
- Precision is micro-averaged over every extracted value, so extras count as false positives.
- New metrics: full-capture rate, turns to full capture, end-reason counts.
- Writes `eval_results.json` and `eval_results.md`, tagged with the mode. The README table is copied from this output.

## 3. Bugs fixed
| Bug | Effect | Fix |
|---|---|---|
| `actual_turns` unbound when a run stopped on its first turn | `UnboundLocalError` crash in `run_conversation` | initialised at loop top |
| Phone digits matched as an account number | wrong account reported, real one missed, precision hurt | phone numbers masked before account extraction (`extractor.py`) |
| Guardrail block not counted when the retry came back clean | "leaks blocked" stayed 0 | block recorded on first failed attempt (`guardrail.py`) |
| Emoji `print` crashed on Windows consoles (cp1252) | `agents.py` / `eval.py` unusable from cmd or PowerShell | stdout reconfigured to UTF-8 |
| `st.secrets` fallback missing | Streamlit Cloud secrets ignored | env first, then `st.secrets` (`app.py`) |

## 4. Tests: 26 -> 40
- `tests/test_loop.py`: ground truth captured per script, repetition circuit breaker, leak blocking in the loop, clear error with no LLM.
- `tests/test_offline.py`: all four scripts fully captured, reproducible by seed, guardrail counted, no 6/12/16-digit numbers in persona output.
- Added a regression test for the phone/account bug.
- Streamlit smoke-tested headlessly (`streamlit.testing`) in Offline and Replay modes with no exceptions.

## 5. Honesty notes
- The README eval table is the **offline** result and says so. The live-LLM eval has not been run; no LLM numbers are claimed.
- All five seeds give the same turn count and time. The persona and scammer RNG is shared by design, so the spread across runs is small. This is a simulator property, not evidence of robustness.

## Still to do (needs you)
Run `python eval.py` with LLM credentials, deploy to Streamlit Community Cloud, record the demo video, and fill the live/video links in `README.md`.
