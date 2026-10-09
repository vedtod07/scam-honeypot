"""
eval.py - Scam Honeypot evaluation.
Runs N conversations per script and reports extraction precision/recall,
turns-to-full-capture, guardrail activity and crash counts.

Usage:
    python eval.py --runs 3             # live LLM (needs LLM_* env vars)
    python eval.py --runs 3 --offline   # deterministic simulator, no API key

Offline numbers measure the pipeline only: the "scammer" and "persona" are
rule-based (see offline.py), and time wasted is simulated, not wall-clock.
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = ["digital_arrest", "kyc", "courier", "upi_collect"]
FIELDS = ["upi_ids", "phone_numbers", "urls", "account_numbers"]


def _counts(found: list, ground_truth: list) -> tuple[int, int, int]:
    """(true positives, extracted total, ground-truth total) for one field."""
    gt_set, found_set = set(ground_truth), set(found)
    return len(gt_set & found_set), len(found_set), len(gt_set)


def _turns_to_full_capture(result: dict, gt: dict, extractor) -> int | None:
    """First scammer turn after which every ground-truth indicator was extracted."""
    acc: dict = {}
    for h in result["history"]:
        if h["role"] != "scammer":
            continue
        acc = extractor.merge_indicators(acc, extractor.extract(h["text"]))
        if all(set(v) <= set(acc.get(f, [])) for f, v in gt.items()):
            return h["turn"]
    return None


def _fmt(x) -> str:
    return "n/a" if x is None else f"{x:.2f}"


def _ratio(num: int, den: int):
    return None if den == 0 else num / den


def run_eval(n_runs: int = 3, offline: bool = False):
    import agents
    import extractor

    script_dir = Path(__file__).parent / "scripts"
    eval_cache = Path(__file__).parent / "cache" / "eval"
    eval_cache.mkdir(parents=True, exist_ok=True)

    rows = []
    for scam_type in SCRIPTS:
        with (script_dir / f"{scam_type}.json").open(encoding="utf-8") as f:
            gt = json.load(f)["ground_truth_indicators"]

        runs, crashes = [], 0
        for i in range(n_runs):
            log_path = eval_cache / f"{scam_type}_run{i + 1}.jsonl"
            log_path.unlink(missing_ok=True)
            try:
                runs.append(agents.run_conversation(
                    scam_type, log_path=str(log_path), offline=offline, seed=i))
            except Exception as exc:  # count crashes honestly, keep going
                print(f"  [CRASH] {scam_type} run {i + 1}: {exc}")
                crashes += 1

        row = {"script": scam_type, "runs": n_runs, "crashes": crashes}
        if runs:
            tp = {f: 0 for f in FIELDS}
            ext = {f: 0 for f in FIELDS}
            tot = {f: 0 for f in FIELDS}
            for r in runs:
                for f in FIELDS:
                    a, b, c = _counts(r["indicators"].get(f, []), gt.get(f, []))
                    tp[f] += a
                    ext[f] += b
                    tot[f] += c
            captures = [_turns_to_full_capture(r, gt, extractor) for r in runs]
            done = [c for c in captures if c is not None]
            row.update({
                "avg_turns": round(sum(r["turns"] for r in runs) / len(runs), 1),
                "avg_time_s": round(sum(r["time_wasted_seconds"] for r in runs) / len(runs), 1),
                "upi_recall": _ratio(tp["upi_ids"], tot["upi_ids"]),
                "phone_recall": _ratio(tp["phone_numbers"], tot["phone_numbers"]),
                "url_recall": _ratio(tp["urls"], tot["urls"]),
                "acct_recall": _ratio(tp["account_numbers"], tot["account_numbers"]),
                # micro-averaged over every extracted value in every field and run
                "precision": _ratio(sum(tp.values()), sum(ext.values())),
                "full_capture_rate": round(len(done) / len(runs), 2),
                "avg_turns_to_full_capture": round(sum(done) / len(done), 1) if done else None,
                "leaks_blocked": sum(r["leaks_blocked"] for r in runs),
                "end_reasons": {k: sum(1 for r in runs if r["end_reason"] == k)
                                for k in sorted({r["end_reason"] for r in runs})},
            })
        rows.append(row)

    header = ("| script | runs | crashes | avg turns | avg time (s) | UPI recall | phone recall "
              "| URL recall | account recall | precision (all fields) | full capture | "
              "turns to full capture | leaks blocked |")
    lines = [header, "|" + "---|" * 13]
    for r in rows:
        if "avg_turns" not in r:
            lines.append(f"| {r['script']} | {r['runs']} | {r['crashes']} |" + " - |" * 10)
            continue
        lines.append(
            f"| {r['script']} | {r['runs']} | {r['crashes']} | {r['avg_turns']} | {r['avg_time_s']} "
            f"| {_fmt(r['upi_recall'])} | {_fmt(r['phone_recall'])} | {_fmt(r['url_recall'])} "
            f"| {_fmt(r['acct_recall'])} | {_fmt(r['precision'])} | {r['full_capture_rate']:.0%} "
            f"| {r['avg_turns_to_full_capture'] if r['avg_turns_to_full_capture'] is not None else 'n/a'} "
            f"| {r['leaks_blocked']} |")
    table = "\n".join(lines)
    mode = ("OFFLINE deterministic simulator (no LLM; time is simulated)" if offline
            else "LIVE LLM")
    print(f"\nMode: {mode}\n\n{table}")

    out = Path(__file__).parent
    (out / "eval_results.json").write_text(
        json.dumps({"mode": "offline" if offline else "llm", "runs_per_script": n_runs,
                    "rows": rows}, indent=2), encoding="utf-8")
    (out / "eval_results.md").write_text(
        f"Mode: {mode}\n\n{table}\n", encoding="utf-8")
    print(f"\nSaved eval_results.json and eval_results.md")
    return rows


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Evaluate Scam Honeypot pipeline")
    parser.add_argument("--runs", type=int, default=3, help="Runs per script")
    parser.add_argument("--offline", action="store_true",
                        help="Use the deterministic simulator instead of an LLM")
    args = parser.parse_args()
    run_eval(args.runs, offline=args.offline)
