import time
from google.genai import types
from extractor import extract, generate, ThreadResult
from thread_parser import Message, format_for_llm

def chunk_messages(messages: list[Message], max_chars=12000, overlap=2):
    """Split on message boundaries; repeat the last `overlap` messages in the next chunk."""
    chunks, cur, size = [], [], 0
    for m in messages:
        length = len(m.body) + 80
        if cur and size + length > max_chars:
            chunks.append(cur)
            cur = cur[-overlap:]
            size = sum(len(x.body) + 80 for x in cur)
        cur.append(m)
        size += length
    if cur:
        chunks.append(cur)
    return chunks

REDUCE_SYSTEM = """You merge partial results from consecutive chunks of ONE email thread.
- Write one 3-5 sentence summary of the whole thread.
- Merge duplicate action items (same task and owner). Keep the original
  source_msg_id and supporting_quote unchanged.
- If a later chunk shows a task is done, set status "done".
- Do not add anything that is not in the partial results."""

def summarize_long(messages: list[Message], max_chars=12000) -> ThreadResult:
    chunks = chunk_messages(messages, max_chars)
    if len(chunks) == 1:
        return extract(format_for_llm(messages))

    partials = []
    for i, c in enumerate(chunks):
        print(f"Chunk {i+1}/{len(chunks)} (msgs {c[0].id}-{c[-1].id})")
        partials.append(extract(format_for_llm(c)))
        time.sleep(2)                       # be gentle with the free tier

    payload = "\n\n".join(
        f"CHUNK {i+1}:\n{p.model_dump_json()}" for i, p in enumerate(partials)
    )
    print("Merging chunks...")
    resp = generate(
        contents=payload,
        config=types.GenerateContentConfig(
            system_instruction=REDUCE_SYSTEM,
            response_mime_type="application/json",
            response_schema=ThreadResult,
            temperature=0.1,
        ),
    )
    return resp.parsed