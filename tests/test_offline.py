"""Offline simulator: full pipeline with no LLM, no network."""
import json
import re

import pytest

import agents

SCRIPTS = ["digital_arrest", "kyc", "courier", "upi_collect"]


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)


@pytest.mark.parametrize("name", SCRIPTS)
def test_offline_captures_all_ground_truth(tmp_path, name):
    res = agents.run_conversation(name, offline=True, seed=1, log_path=str(tmp_path / "r.jsonl"))
    with open(f"scripts/{name}.json", encoding="utf-8") as f:
        gt = json.load(f)["ground_truth_indicators"]
    for field, vals in gt.items():
        assert set(vals) <= set(res["indicators"][field]), (name, field)
    assert res["simulated"] is True
    assert res["time_wasted_seconds"] > 60  # simulated, not wall-clock


def test_offline_is_reproducible(tmp_path):
    a = agents.run_conversation("kyc", offline=True, seed=3, log_path=str(tmp_path / "a.jsonl"))
    b = agents.run_conversation("kyc", offline=True, seed=3, log_path=str(tmp_path / "b.jsonl"))
    assert [h["text"] for h in a["history"]] == [h["text"] for h in b["history"]]


def test_guardrail_counts_blocked_leaks_and_logs_are_clean(tmp_path):
    total = 0
    for seed in range(5):
        res = agents.run_conversation("digital_arrest", offline=True, seed=seed,
                                      log_path=str(tmp_path / f"r{seed}.jsonl"))
        persona = [h["text"] for h in res["history"] if h["role"] == "persona"]
        assert not any(re.search(r"(\d{6}|\d{12}|\d{16})", t) for t in persona)
        total += res["leaks_blocked"]
    assert total >= 1
