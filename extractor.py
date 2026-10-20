import os, time
from pydantic import BaseModel
from google import genai
from google.genai import types

MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
]
MODEL = MODELS[0]

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options=types.HttpOptions(timeout=90_000),
)

def generate(contents, config, retries=2):
    """Retry on temporary errors with backoff, then fall back to the next model."""
    TEMP = ("503", "504", "500", "502", "429", "UNAVAILABLE",
            "DEADLINE", "timed out", "timeout", "overloaded")
    last = None
    for model in MODELS:
        for attempt in range(retries):
            try:
                print(f"[{model}] attempt {attempt+1}...")
                return client.models.generate_content(
                    model=model, contents=contents, config=config
                )
            except Exception as e:
                last = e
                msg = str(e)
                if "404" in msg or "NOT_FOUND" in msg:
                    break                      # model not available, next model
                if any(t.lower() in msg.lower() for t in TEMP):
                    wait = 5 * (attempt + 1)
                    print(f"  temporary error ({msg[:60]}...), retry in {wait}s")
                    time.sleep(wait)
                else:
                    raise                      # real error (bad key, bad schema)
    raise last


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
- If the owner is not clear, use "Unassigned". If no deadline, use "None".
- supporting_quote must be copied EXACTLY from the message at source_msg_id.
- If a later message says a task is done, mark status "done".
- Only extract tasks that someone is asked to do, or commits to doing.
- Do NOT extract questions ("should I order lunch?") or suggestions that
  were rejected or cancelled.
- If a task is cancelled, leave it out.
- Summary: 3-5 sentences."""

def extract(thread_text: str) -> ThreadResult:
    resp = generate(
    contents=thread_text,
    config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
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