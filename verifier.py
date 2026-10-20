import re
import time
from pydantic import BaseModel
from google.genai import types
from extractor import client, MODEL, ThreadResult, generate
from thread_parser import Message

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()

# ---------- Check 1: exact quote matching (no LLM) ----------
def check_quotes(result: ThreadResult, messages: list[Message]) -> list[bool]:
    by_id = {m.id: norm(m.body) for m in messages}
    return [
        norm(a.supporting_quote) in by_id.get(a.source_msg_id, "")
        for a in result.action_items
    ]

# ---------- Check 2: LLM verifier ----------
class Verdict(BaseModel):
    claim: str
    supported: bool
    reason: str

class VerdictList(BaseModel):
    verdicts: list[Verdict]

VERIFY_SYSTEM = """You are a strict fact-checker. For each claim, decide if the
email thread supports it. Mark supported=false only if the claim contradicts the
thread or adds names, dates, tasks or outcomes that are not in it. Status
"done" is supported if a later message says the work was completed or sent.
Keep reason to one line."""

def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

def build_claims(result: ThreadResult) -> list[str]:
    claims = split_sentences(result.summary)
    claims += result.decisions
    claims += [
        f"Action item: '{a.task}' | owner: {a.owner} | deadline: {a.deadline} | status: {a.status}"
        for a in result.action_items
    ]
    return claims


def verify_claims(thread_text: str, claims: list[str]) -> list[Verdict]:
    prompt = "THREAD:\n" + thread_text + "\n\nCLAIMS:\n" + "\n".join(
        f"{i+1}. {c}" for i, c in enumerate(claims)
    )
    resp = generate(
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=VERIFY_SYSTEM,
            response_mime_type="application/json",
            response_schema=VerdictList,
            temperature=0.0,
        ),
    )
    return resp.parsed.verdicts

def filter_verified(result, messages):
    ok = check_quotes(result, messages)
    result.action_items = [a for a, good in zip(result.action_items, ok) if good]
    return result

# ---------- Combine ----------
def faithfulness_report(result: ThreadResult, messages: list[Message], thread_text: str) -> dict:
    quote_ok = check_quotes(result, messages)
    verdicts = verify_claims(thread_text, build_claims(result))
    supported = sum(v.supported for v in verdicts)
    return {
        "quote_match": f"{sum(quote_ok)}/{len(quote_ok)}",
        "claims_supported": f"{supported}/{len(verdicts)}",
        "faithfulness_score": round(supported / max(len(verdicts), 1), 2),
        "unsupported": [v for v in verdicts if not v.supported],
        "bad_quotes": [a.task for a, ok in zip(result.action_items, quote_ok) if not ok],
    }

if __name__ == "__main__":
    from thread_parser import parse_thread, format_for_llm
    from extractor import extract
    raw = open("data/thread1.txt", encoding="utf-8").read()
    msgs = parse_thread(raw)
    text = format_for_llm(msgs)
    result = extract(text)
    report = faithfulness_report(result, msgs, text)
    print("Quote match:     ", report["quote_match"])
    print("Claims supported:", report["claims_supported"])
    print("Faithfulness:    ", report["faithfulness_score"])
    print("Unsupported:     ", report["unsupported"])
    print("Bad quotes:      ", report["bad_quotes"])