"""
eval.py — Scam Honeypot Phase 4
Runs N conversations per script and reports extraction precision/recall.

Usage:
    python eval.py --runs 3
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _precision_recall(found: list, ground_truth: list) -> tuple[float, float]:
    if not ground_truth:
        return (1.0, 1.0)  # vacuously perfect
    gt_set = set(ground_truth)
    found_set = set(found)
    true_pos = len(gt_set & found_set)
    recall = true_pos / len(gt_set)
    precision = true_pos / len(found_set) if found_set else 0.0
    return precision, recall


def run_eval(n_runs: int = 3):
    import agents
    import extractor

    scripts = ["digital_arrest", "kyc", "courier", "upi_collect"]
    script_dir = Path(__file__).parent / "scripts"
    eval_cache = Path(__file__).parent / "cache" / "eval"
    eval_cache.mkdir(parents=True, exist_ok=True)

    all_results = {}
    rows = []

    for scam_type in scripts:
        with (script_dir / f"{scam_type}.json").open() as f:
            script = json.load(f)
        gt = script["ground_truth_indicators"]

        run_results = []
        crashes = 0

        for run_idx in range(n_runs):
            log_path = str(eval_cache / f"{scam_type}_run{run_idx+1}.jsonl")
            try:
                result = agents.run_conversation(scam_type, log_path=log_path)
                run_results.append(result)
            except Exception as exc:
                print(f"  [CRASH] {scam_type} run {run_idx+1}: {exc}")
                crashes += 1

        if not run_results:
            rows.append({
                "script": scam_type, "runs": n_runs, "crashes": crashes,
                "avg_turns": 0, "avg_time_s": 0,
                "upi_recall": 0, "phone_recall": 0,
                "url_recall": 0, "acct_recall": 0,
                "precision": 0, "leaks_blocked": 0,
            })
            continue

        avg_turns = sum(r["turns"] for r in run_results) / len(run_results)
        avg_time = sum(r["time_wasted_seconds"] for r in run_results) / len(run_results)
        total_leaks = sum(r["leaks_blocked"] for r in run_results)

        # Aggregate field precision/recall across runs
        field_metrics = {
            "upi_ids": [], "phone_numbers": [], "urls": [], "account_numbers": []
        }
        for r in run_results:
            ind = r["indicators"]
            for field in field_metrics:
                p, rec = _precision_recall(ind.get(field, []), gt.get(field, []))
                field_metrics[field].append((p, rec))

        def avg_pr(field):
            vals = field_metrics[field]
            if not vals:
                return 0.0, 0.0
            return (
                sum(v[0] for v in vals) / len(vals),
                sum(v[1] for v in vals) / len(vals),
            )

        upi_p, upi_r = avg_pr("upi_ids")
        ph_p, ph_r = avg_pr("phone_numbers")
        url_p, url_r = avg_pr("urls")
        acct_p, acct_r = avg_pr("account_numbers")

        # Overall precision = avg across all fields
        all_precisions = [upi_p, ph_p, url_p, acct_p]
        overall_p = sum(all_precisions) / len(all_precisions)

        rows.append({
            "script": scam_type,
            "runs": n_runs,
            "crashes": crashes,
            "avg_turns": round(avg_turns, 1),
            "avg_time_s": round(avg_time, 1),
            "upi_recall": round(upi_r, 2),
            "phone_recall": round(ph_r, 2),
            "url_recall": round(url_r, 2),
            "acct_recall": round(acct_r, 2),
            "precision": round(overall_p, 2),
            "leaks_blocked": total_leaks,
        })
        all_results[scam_type] = run_results

    # Print markdown table
    header = "| script | runs | crashes | avg turns | avg time (s) | UPI recall | phone recall | URL recall | account recall | precision (all fields) | leaks blocked |"
    sep    = "|---|---|---|---|---|---|---|---|---|---|---|"
    print("\n" + header)
    print(sep)
    for r in rows:
        print(
            f"| {r['script']} | {r['runs']} | {r['crashes']} | {r['avg_turns']} "
            f"| {r['avg_time_s']} | {r['upi_recall']} | {r['phone_recall']} "
            f"| {r['url_recall']} | {r['acct_recall']} | {r['precision']} | {r['leaks_blocked']} |"
        )

    # Save results
    out_path = Path(__file__).parent / "eval_results.json"
    with out_path.open("w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nResults saved to {out_path}")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Scam Honeypot pipeline")
    parser.add_argument("--runs", type=int, default=3, help="Runs per script")
    args = parser.parse_args()
    run_eval(args.runs)
