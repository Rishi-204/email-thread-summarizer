import os
import time
from pydantic import BaseModel
from google import genai
from google.genai import types
from tenacity import (retry, stop_after_attempt,
                      wait_exponential_jitter, retry_if_exception)
from audit import log_event

# Tried in order; lite models are usually less busy on the free tier
MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
]
MODEL = MODELS[0]

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options=types.HttpOptions(timeout=90_000),  # 90 seconds
)


class ActionItem(BaseModel):
    task: str
    owner: str             # person name, or "Unassigned"
    deadline: str          # as stated in thread, or "None"
    source_msg_id: int
    supporting_quote: str  # exact text copied from that message
    status: str            # "open" or "done"


class ThreadResult(BaseModel):
    summary: str
    decisions: list[str]
    action_items: list[ActionItem]


SYSTEM = """You summarise email threads and extract action items.
Rules:
- Use ONLY information in the thread. Never invent owners, deadlines or tasks.
- A question that asks someone to DO something ("can you approve the credit note?")
  is a task. A question about WHETHER to do something ("should we order lunch?")
  is not a task.
- If one sentence contains several separate commitments ("I'll fix X and add Y"),
  list each as its own action item.
- A task nobody has claimed ("someone should update the docs") is extracted with
  owner "Unassigned".
- If a task is cancelled or a suggestion was rejected, leave it out.
- If a task was reassigned, the final owner is the owner.
- If the deadline changed, use the latest deadline.
- If the owner is not clear, use "Unassigned". If no deadline, use "None".
- supporting_quote must be copied EXACTLY from the message at source_msg_id.
- status is "done" if a later message says the task was completed, else "open".
- Summary: 3-5 sentences."""

# Added when earlier chunks already found tasks (rolling state across chunks)
UPDATE_NOTE = """
The input may start with KNOWN OPEN ACTION ITEMS found in earlier messages.
They are context only.
- If messages in THIS chunk show one of them was completed, reassigned, or its
  deadline changed, output that item again with the SAME task wording, the updated
  owner/status/deadline, and source_msg_id and supporting_quote taken from the
  message in THIS chunk that shows the change.
- Do NOT repeat known items that this chunk does not change.
- New tasks in this chunk are extracted as usual."""


# ---------- Reliability: exponential backoff + model fallback ----------
def _is_temporary(e: Exception) -> bool:
    msg = str(e).lower()
    return any(t in msg for t in (
        "503", "504", "500", "502", "429", "unavailable", "deadline",
        "timed out", "timeout", "overloaded", "connection", "reset",
        "getaddrinfo", "connect"))


def _is_missing_model(e: Exception) -> bool:
    return "404" in str(e) or "not_found" in str(e).lower()


def _log_retry(rs):
    err = str(rs.outcome.exception())
    print(f"  retry {rs.attempt_number} after: {err[:70]}")
    log_event("retry", attempt=rs.attempt_number, error=err[:120])


def generate(contents, config):
    """Exponential backoff with jitter per model; fall back to the next model."""
    last = None
    for model in MODELS:
        @retry(stop=stop_after_attempt(4),
               wait=wait_exponential_jitter(initial=2, max=30),
               retry=retry_if_exception(_is_temporary),
               before_sleep=_log_retry, reraise=True)
        def _call():
            print(f"[{model}] calling...")
            return client.models.generate_content(
                model=model, contents=contents, config=config)
        started = time.time()
        try:
            resp = _call()
            log_event("llm_call", model=model, ok=True,
                      seconds=round(time.time() - started, 2))
            return resp
        except Exception as e:
            last = e
            log_event("llm_call", model=model, ok=False,
                      seconds=round(time.time() - started, 2), error=str(e)[:120])
            if _is_missing_model(e) or _is_temporary(e):
                continue            # try the next model
            raise                   # real error (bad key, bad schema)
    raise last


def extract(thread_text: str, known_items=None) -> ThreadResult:
    contents, system = thread_text, SYSTEM
    if known_items:
        known = "\n".join(it.model_dump_json() for it in known_items)
        contents = (f"KNOWN OPEN ACTION ITEMS (from earlier messages):\n{known}\n\n"
                    f"THREAD CHUNK:\n{thread_text}")
        system = SYSTEM + UPDATE_NOTE
    resp = generate(
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=ThreadResult,
            temperature=0.1,
        ),
    )
    return resp.parsed


if __name__ == "__main__":
    from thread_parser import parse_thread, format_for_llm
    raw = open("data/thread1.txt", encoding="utf-8").read()
    result = extract(format_for_llm(parse_thread(raw)))
    print(result.model_dump_json(indent=2))
