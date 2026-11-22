# Model Card: Email Thread Summarizer & Action Tracker (PS 78)

## Summary
A pipeline (not a trained model) that turns an email thread into a summary, decisions,
and action items with owner, deadline, status and a proof quote. It calls a hosted
LLM (Google Gemini, free tier) and checks the output before showing it.

## Intended use
- Catching up on long internal threads; tracking who owns which follow-up.
- A human reads the result and uses the evidence column to confirm each item.

## Out of scope / not recommended
- Legal, medical, HR or financial decisions made from the output alone.
- Automatic task creation or reminders with no human review.
- Non-English threads and heavily forwarded or HTML-only emails (not tested).

## How it works
1. Parse the thread, strip quoted replies and signatures.
2. Mask names, emails and phone numbers with stable placeholders (optional, on by default).
3. Extract schema-bound JSON (pydantic) at temperature 0.1.
4. Long threads: token-based chunks with overlap, extraction per chunk with a rolling
   list of open items, code-level de-duplication, then an LLM reconciliation pass.
5. Verify: exact-quote match in code, then an LLM claim-by-claim check.
6. Restore real names locally and display with a faithfulness score.

Models: Gemini flash / flash-lite family with automatic fallback when one is busy
(see `MODELS` in `extractor.py`). Backoff with jitter via `tenacity`.

## Evaluation
20 hand-written threads, 41 gold action items (`data/labels.json`), one-to-one matching
of predicted to gold items (`eval.py`). Latest full run:

| Metric | Value |
|---|---|
| Precision | 1.00 |
| Recall | 0.93 |
| F1 | 0.96 |
| Status accuracy | 1.00 |
| Deadline accuracy | 1.00 |
| Avg faithfulness (self-checked) | 0.99 |

Per-thread results and missed items: `results.md`.

## Known limitations
- **Small, synthetic test set.** Metrics are indicative, not statistically strong.
- **Tuned on the test set.** Prompt rules were adjusted after seeing failures on these
  threads; a fresh held-out set is needed for an unbiased number.
- **Non-deterministic.** The same thread can give slightly different items between runs;
  report ranges over several runs.
- **Self-checked faithfulness.** The verifier is the same model family as the extractor
  and can give false positives or miss errors. The exact-quote check is the independent layer.
- **Failure modes seen:** a question turned into a task; two commitments in one sentence
  merged into one; an unclaimed "someone should..." dropped (before the prompt fix).
- **Chunking** did not improve accuracy on threads that fit the context window; it is for
  threads beyond the token budget and for cost/latency control.
- **Masking is rule-based:** names that never appear in a `From:` header are not masked.

## Privacy and data handling
- Names, emails and phones are replaced with placeholders before any API call and restored
  locally; the "What the API sees" panel shows exactly what is sent.
- Nothing is stored by default. The optional demo cache writes results to `cache/` (ignored by git).
- The audit log (`logs/audit.jsonl`, ignored by git) never contains raw thread text. Task and
  quote text is logged only when masking is on (placeholders only); otherwise only hashes.
- The text still goes to a third-party API (Google). For sensitive mail use a local model.

## Monitoring and audit
Every LLM call (model, latency, retries, fallbacks) and every action item with its proof
quote and verification result is written to the audit log as JSON lines.

## Testing and CI
`pytest` runs 18 offline tests (parser, privacy, chunking and rolling state, dedupe,
quote checking, audit log) on every push via GitHub Actions. The live evaluation is a
manual workflow because it makes ~60 API calls.

## Version
v0.5, November 2026. Maintainers: project team (see repository).
