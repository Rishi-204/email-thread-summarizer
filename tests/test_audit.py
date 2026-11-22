import json
import audit
from extractor import ActionItem, ThreadResult
from verifier import Verdict


def _result():
    a = ActionItem(task="Send the report", owner="[PERSON_1]", deadline="Friday",
                   source_msg_id=1, supporting_quote="[PERSON_1], please send the report",
                   status="open")
    return ThreadResult(summary="s", decisions=[], action_items=[a])


def _report():
    return {"faithfulness_score": 0.9, "quote_match": "1/1",
            "unsupported": [Verdict(claim="secret claim", supported=False, reason="r")]}


def _read(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]


def test_masked_run_logs_claim_and_proof_quote(tmp_path, monkeypatch):
    log = tmp_path / "a.jsonl"
    monkeypatch.setattr(audit, "LOG_PATH", str(log))
    audit.log_run("raw thread", _result(), _report(), [True], masked=True)
    rows = _read(log)
    kinds = [r["kind"] for r in rows]
    assert kinds == ["run", "claim", "unsupported_claim"]
    claim = rows[1]
    assert claim["proof_quote"] == "[PERSON_1], please send the report"
    assert claim["quote_verified"] is True


def test_unmasked_run_logs_hashes_only(tmp_path, monkeypatch):
    log = tmp_path / "b.jsonl"
    monkeypatch.setattr(audit, "LOG_PATH", str(log))
    audit.log_run("raw thread", _result(), _report(), [False], masked=False)
    text = log.read_text(encoding="utf-8")
    assert "Send the report" not in text and "secret claim" not in text
    assert "task_hash" in text and "quote_hash" in text


def test_logging_never_raises(monkeypatch):
    monkeypatch.setattr(audit, "LOG_PATH", "/proc/not/writable/x.jsonl")
    audit.log_event("retry", attempt=1)         # must not raise
