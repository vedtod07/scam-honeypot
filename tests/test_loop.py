"""Turn-loop tests with stubbed LLM roles (no network, no API key needed)."""
import json

import pytest

import agents

SCRIPTS = ["digital_arrest", "kyc", "courier", "upi_collect"]


def _gt(name):
    with open(f"scripts/{name}.json", encoding="utf-8") as f:
        return json.load(f)["ground_truth_indicators"]


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(agents.extractor, "_llm_extract", lambda *a, **k: None, raising=False)


def _varied_persona(counter=[0]):
    def fn(history, canary):
        counter[0] += 1
        return f"Haan ji beta, stall variant number {counter[0]} please wait for me?"
    return fn


@pytest.mark.parametrize("name", SCRIPTS)
def test_loop_captures_ground_truth(monkeypatch, tmp_path, name):
    monkeypatch.setattr(agents, "persona_reply", _varied_persona([0]))
    gt0 = _gt(name)
    facts = " ".join(f"Contact {v}" if f != "account_numbers" else f"account number {v}" for f, vals in gt0.items() for v in vals)
    monkeypatch.setattr(
        agents, "scammer_reply",
        lambda h, s: f"Details for step {len(h)} " + "xyzabc"[len(h) % 6] * (len(h) % 5 + 1) + " " + facts,
    )
    res = agents.run_conversation(name, max_turns=3, log_path=str(tmp_path / "r.jsonl"))
    gt = _gt(name)
    for field, vals in gt.items():
        for v in vals:
            assert v in res["indicators"].get(field, []), (name, field, v)
    lines = (tmp_path / "r.jsonl").read_text(encoding="utf-8").splitlines()
    assert all(json.loads(l) for l in lines)


def test_repetition_circuit_breaker(monkeypatch, tmp_path):
    monkeypatch.setattr(agents, "persona_reply", lambda h, c: "My phone is hanging, one minute please.")
    monkeypatch.setattr(agents, "scammer_reply", lambda h, s: "Please wait.")
    res = agents.run_conversation("kyc", log_path=str(tmp_path / "r.jsonl"))
    assert res["end_reason"] == "repetition"
    assert res["turns"] < 14


def test_leak_is_blocked_in_loop(monkeypatch, tmp_path):
    monkeypatch.setattr(agents, "persona_reply", lambda h, c: "My OTP is 483920, beta.")
    monkeypatch.setattr(agents, "scammer_reply", lambda h, s: "ok")
    res = agents.run_conversation("kyc", max_turns=2, log_path=str(tmp_path / "r.jsonl"))
    assert res["leaks_blocked"] >= 1
    persona_text = " ".join(h["text"] for h in res["history"] if h["role"] == "persona")
    assert "483920" not in persona_text


def test_no_llm_raises_clear_error(tmp_path):
    with pytest.raises(EnvironmentError):
        agents.run_conversation("kyc", max_turns=1, log_path=str(tmp_path / "r.jsonl"))
