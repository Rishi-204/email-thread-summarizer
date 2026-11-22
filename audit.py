"""Structured audit log (JSON lines). Never raises, never logs raw thread text.

- LLM calls, retries and fallbacks: model, seconds, error code only.
- Per run: counts, faithfulness, and every action item with its proof quote.
  Task/quote TEXT is written only when PII masking was on (so it contains
  placeholders, not real names). With masking off, only hashes are written.
"""
import datetime
import hashlib
import json
import os

LOG_PATH = os.environ.get("SUMMARIZER_LOG", os.path.join("logs", "audit.jsonl"))


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def log_event(kind: str, **fields) -> None:
    try:
        os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _now(), "kind": kind, **fields},
                               ensure_ascii=False) + "\n")
    except Exception:
        pass   # logging must never break the app


def log_run(raw: str, result, report, quote_ok, masked: bool, meta=None) -> str:
    """Log one summarisation run plus one record per action item (claim + proof quote)."""
    run_id = short_hash(raw + _now())
    log_event("run", run_id=run_id, thread=short_hash(raw), masked=masked,
              items=len(result.action_items),
              faithfulness=report["faithfulness_score"] if report else None,
              quotes_verified=report["quote_match"] if report else None,
              **(meta or {}))
    for a, ok in zip(result.action_items, quote_ok):
        rec = {"run_id": run_id, "source_msg_id": a.source_msg_id,
               "status": a.status, "quote_verified": ok}
        if masked:
            rec.update(task=a.task, owner=a.owner, deadline=a.deadline,
                       proof_quote=a.supporting_quote)
        else:
            rec.update(task_hash=short_hash(a.task),
                       quote_hash=short_hash(a.supporting_quote))
        log_event("claim", **rec)
    if report:
        for v in report["unsupported"]:
            rec = {"run_id": run_id, "supported": False}
            if masked:
                rec.update(claim=v.claim, reason=v.reason)
            else:
                rec.update(claim_hash=short_hash(v.claim))
            log_event("unsupported_claim", **rec)
    return run_id
