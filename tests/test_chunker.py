from types import SimpleNamespace
import chunker
from chunker import chunk_by_tokens, dedupe_items, thread_tokens
from extractor import ActionItem, ThreadResult
from thread_parser import Message


def item(owner, task, status="open", deadline="None", src=1, quote="q"):
    return ActionItem(task=task, owner=owner, deadline=deadline,
                      source_msg_id=src, supporting_quote=quote, status=status)


def test_chunks_cover_every_message_and_overlap():
    msgs = [Message(i, "A", "d", "word " * 60) for i in range(1, 41)]
    chunks = chunk_by_tokens(msgs, 400, 2)
    assert len(chunks) > 1
    assert {m.id for c in chunks for m in c} == {m.id for m in msgs}
    assert chunks[-1][-1].id == 40
    for a, b in zip(chunks, chunks[1:]):
        assert a[-1].id >= b[0].id          # overlap, no gap


def test_dedupe_merges_same_owner_and_keeps_done_and_latest_deadline():
    out = dedupe_items([
        item("Bob", "Prepare the vendor contract draft", "open", "15 Oct", 3),
        item("Bob", "prepare the vendor contract", "done", "None", 51),
    ])
    assert len(out) == 1
    assert out[0].status == "done" and out[0].deadline == "15 Oct"
    assert out[0].source_msg_id == 3        # first mention keeps its citation


def test_dedupe_keeps_different_owners_and_different_tasks_apart():
    out = dedupe_items([
        item("Tushar", "Send availability"), item("Anita", "Send availability"),
        item("Arvind", "Fix the null check"), item("Arvind", "Add tests for empty input"),
    ])
    assert len(out) == 4


def test_rolling_state_updates_task_from_earlier_chunk(monkeypatch):
    """The weak spot from Step 3: a 'done' message that creates no new task."""
    msgs = [Message(i, "A", "d", "ok noted " * 10) for i in range(1, 31)]
    msgs[2].body = "Bob, please prepare the contract."
    msgs[24].body = "The contract is done."
    seen = []

    def fake_extract(text, known_items=None):
        seen.append(known_items)
        items = []
        if "please prepare the contract" in text:
            items.append(item("Bob", "Prepare the contract", src=3,
                              quote="Bob, please prepare the contract."))
        if "The contract is done" in text and known_items:
            items.append(known_items[0].model_copy(update={
                "status": "done", "source_msg_id": 25,
                "supporting_quote": "The contract is done."}))
        return ThreadResult(summary="s", decisions=[], action_items=items)

    def fake_generate(contents, config):       # reconcile step just echoes candidates
        lines = contents.split("CANDIDATE ACTION ITEMS:\n")[1].splitlines()
        items = [ActionItem.model_validate_json(l) for l in lines if l.strip()]
        return SimpleNamespace(parsed=ThreadResult(summary="s", decisions=[],
                                                    action_items=items))

    monkeypatch.setattr(chunker, "extract", fake_extract)
    monkeypatch.setattr(chunker, "generate", fake_generate)
    monkeypatch.setattr(chunker.time, "sleep", lambda s: None)

    result = chunker.summarize_long(msgs, chunk_tokens=100, single_pass_limit=0,
                                    verbose=False)
    assert seen[0] is None                      # first chunk has no prior state
    assert any(k for k in seen[1:])             # later chunks receive open items
    assert len(result.action_items) == 1
    assert result.action_items[0].status == "done"


def test_short_thread_uses_single_pass(monkeypatch):
    calls = []
    monkeypatch.setattr(chunker, "extract",
                        lambda text, known_items=None: calls.append(text) or
                        ThreadResult(summary="s", decisions=[], action_items=[]))
    msgs = [Message(1, "A", "d", "hello")]
    chunker.summarize_long(msgs, verbose=False)
    assert len(calls) == 1 and thread_tokens(msgs) < chunker.SINGLE_PASS_LIMIT
