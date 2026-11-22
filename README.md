# Email Thread Summarizer & Action Tracker (PS 78)

Turns a long email thread into a summary, decisions, and action items with owners,
deadlines, status, and source evidence.

## Pipeline
1. **Parse** (`thread_parser.py`): split messages, strip quotes and signatures
2. **Mask PII** (`privacy.py`): names, emails and phones become placeholders before the API call, restored afterwards
3. **Extract** (`extractor.py`): Gemini returns schema-constrained JSON (pydantic)
4. **Chunk** (`chunker.py`): split on message boundaries with overlap, then a merge pass
5. **Verify** (`verifier.py`): exact-quote match plus an LLM claim checker
6. **UI** (`app.py`): Streamlit app with faithfulness badge

## Setup
```
python -m venv venv && venv\Scripts\activate
pip install -U google-genai pydantic streamlit pandas
$env:GEMINI_API_KEY="your_key"
streamlit run app.py
```

## Evaluation (eval.py, 20 labelled threads, 41 gold action items)
Precision 1.00 | Recall 0.93 | F1 0.96 | Status accuracy 1.00 | Deadline accuracy 1.00 | Avg faithfulness 0.99
One-to-one matching; per-thread results and missed items in results.md

## Limitations
- Small test set; the metrics are indicative, not statistically strong
- The LLM verifier can produce false positives, so the exact-quote check is the more reliable layer
- Rule-based PII masking can miss names not present in sender headers (use Presidio/NER in production)
- Free-tier Gemini has latency spikes (503s), handled by retry plus model fallback