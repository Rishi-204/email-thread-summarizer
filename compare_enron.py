"""Single pass vs chunked + reconciliation on real (Enron) threads. PII masking is ON."""
import glob
from thread_parser import parse_thread, format_for_llm
from chunker import summarize_long, thread_tokens
from privacy import mask_messages
from verifier import faithfulness_report

for path in sorted(glob.glob("data/enron_*.txt")):
    msgs, _ = mask_messages(parse_thread(open(path, encoding="utf-8").read()))
    toks = thread_tokens(msgs)
    text = format_for_llm(msgs)
    print(f"\n=== {path}: {len(msgs)} messages, ~{toks} tokens ===")
    modes = {
        "single": dict(single_pass_limit=10**9),
        "chunked": dict(chunk_tokens=max(800, toks // 4), single_pass_limit=0),
    }
    for name, kw in modes.items():
        try:
            r = summarize_long(msgs, verbose=False, **kw)
            rep = faithfulness_report(r, msgs, text)
        except Exception as e:
            print(f"  {name}: FAILED ({str(e)[:80]})")
            continue
        print(f"  {name}: {len(r.action_items)} items | faithfulness "
              f"{rep['faithfulness_score']} | quotes {rep['quote_match']}")
        for a in r.action_items:
            print(f"      - {a.owner}: {a.task} [{a.status}] ({a.deadline})")
