import time
from difflib import SequenceMatcher
from google.genai import types
from extractor import extract, generate, ThreadResult
from thread_parser import Message, format_for_llm

SINGLE_PASS_LIMIT = 30_000   # tokens; below this one call is enough
CHUNK_TOKENS = 6_000         # tokens per chunk when a thread is longer
DONE = ("done", "completed", "complete")


# ---------- token estimation (offline, ~4 characters per token) ----------
def estimate_tokens(text: str) -> int:
    return len(text) // 4 + 1


def message_tokens(m: Message) -> int:
    return estimate_tokens(m.body) + 20      # + header line overhead


def thread_tokens(messages: list[Message]) -> int:
    return sum(message_tokens(m) for m in messages)


def chunk_by_tokens(messages: list[Message], max_tokens=CHUNK_TOKENS, overlap=2):
    """Split on message boundaries; repeat the last `overlap` messages in the next chunk."""
    chunks, cur, size = [], [], 0
    for m in messages:
        t = message_tokens(m)
        if cur and size + t > max_tokens:
            chunks.append(cur)
            cur = cur[-overlap:] if overlap else []
            size = sum(message_tokens(x) for x in cur)
        cur.append(m)
        size += t
    if cur:
        chunks.append(cur)
    return chunks


# ---------- deterministic part of reconciliation ----------
def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def dedupe_items(items, threshold=0.6):
    """Merge items with the same owner and a similar task (items are in chunk order).
    Keeps the first mention's source and quote; 'done' is sticky; latest deadline wins."""
    groups = []
    for it in items:
        for g in groups:
            if g[0].owner.strip().lower() == it.owner.strip().lower() \
                    and _sim(g[0].task, it.task) >= threshold:
                g.append(it)
                break
        else:
            groups.append([it])
    out = []
    for g in groups:
        merged = g[0].model_copy()
        merged.status = "done" if any(x.status.strip().lower() in DONE for x in g) else "open"
        deadlines = [x.deadline for x in g if x.deadline.strip().lower() not in ("", "none")]
        merged.deadline = deadlines[-1] if deadlines else "None"
        out.append(merged)
    return out


# ---------- LLM part of reconciliation ----------
RECONCILE_SYSTEM = """You reconcile partial results from consecutive chunks of ONE email thread.
Chunks are in time order; later chunks are more recent and override earlier ones.
Input: per-chunk summaries and decisions, plus a candidate action-item list that
code has already de-duplicated.
Output:
- summary: 3-5 sentences about the WHOLE thread.
- decisions: final decisions only (drop any that were later reversed).
- action_items: start from the candidate list and fix it:
  * If the same task appears with different owners, keep only the LATEST owner (reassignment).
  * Remove tasks that a later chunk cancelled or rejected.
  * If a later chunk shows a task is done, status is "done"; if its deadline changed, use the latest deadline.
  * Keep source_msg_id and supporting_quote exactly as given. Never add new tasks."""


def summarize_long(messages: list[Message],
                   chunk_tokens: int = CHUNK_TOKENS,
                   single_pass_limit: int = SINGLE_PASS_LIMIT,
                   overlap: int = 2,
                   verbose: bool = True) -> ThreadResult:
    total = thread_tokens(messages)
    if total <= single_pass_limit:
        if verbose:
            print(f"~{total} tokens <= {single_pass_limit}: single pass")
        return extract(format_for_llm(messages))

    chunks = chunk_by_tokens(messages, chunk_tokens, overlap)
    if len(chunks) == 1:
        return extract(format_for_llm(messages))
    if verbose:
        print(f"~{total} tokens > {single_pass_limit}: {len(chunks)} chunks of ~{chunk_tokens}")

    partials, all_items = [], []
    for i, c in enumerate(chunks):
        if verbose:
            print(f"Chunk {i + 1}/{len(chunks)} (msgs {c[0].id}-{c[-1].id})")
        # rolling state: later chunks see the still-open items found so far, so a
        # message like "the contract is done" can update a task from an earlier chunk
        known_open = [it for it in dedupe_items(all_items)
                      if it.status.strip().lower() not in DONE]
        part = extract(format_for_llm(c), known_items=known_open or None)
        partials.append(part)
        all_items.extend(part.action_items)        # chunk order
        if i < len(chunks) - 1:
            time.sleep(2)                          # be gentle with the free tier

    candidates = dedupe_items(all_items)

    payload = "CHUNKS (oldest first):\n" + "\n".join(
        f"CHUNK {i + 1} (msgs {c[0].id}-{c[-1].id}): summary={p.summary} | decisions={p.decisions}"
        for i, (c, p) in enumerate(zip(chunks, partials))
    ) + "\n\nCANDIDATE ACTION ITEMS:\n" + "\n".join(
        it.model_dump_json() for it in candidates
    )
    if verbose:
        print(f"Reconciling ({len(all_items)} raw items -> {len(candidates)} after dedupe)...")
    resp = generate(
        contents=payload,
        config=types.GenerateContentConfig(
            system_instruction=RECONCILE_SYSTEM,
            response_mime_type="application/json",
            response_schema=ThreadResult,
            temperature=0.1,
        ),
    )
    return resp.parsed
