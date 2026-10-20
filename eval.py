import json, time
from thread_parser import parse_thread, format_for_llm
from chunker import summarize_long
from verifier import faithfulness_report

labels = json.load(open("data/labels.json", encoding="utf-8"))

def norm_status(s):
    return "done" if s.strip().lower() in ("done", "completed", "complete") else "open"

def matches(pred, gold):
    task = pred.task.lower()
    return (pred.owner.strip().lower() == gold["owner"].lower()
            and all(k in task for k in gold["keywords"]))

tot_pred = tot_gold = tot_tp = tot_gold_hit = status_ok = 0
faith_scores = []

for fname, gold in labels.items():
    raw = open(f"data/{fname}", encoding="utf-8").read()
    msgs = parse_thread(raw)
    result = summarize_long(msgs)
    preds = result.action_items

    tp = sum(any(matches(p, g) for g in gold) for p in preds)
    hit = 0
    for g in gold:
        m = next((p for p in preds if matches(p, g)), None)
        if m:
            hit += 1
            status_ok += norm_status(m.status) == g["status"]

    rep = faithfulness_report(result, msgs, format_for_llm(msgs))
    faith_scores.append(rep["faithfulness_score"])

    p = tp / max(len(preds), 1)
    r = hit / len(gold)
    print(f"\n{fname}: precision={p:.2f} recall={r:.2f} faithfulness={rep['faithfulness_score']}")
    for a in preds:
        print(f"   - {a.owner}: {a.task} [{a.status}]")

    tot_pred += len(preds); tot_gold += len(gold)
    tot_tp += tp; tot_gold_hit += hit
    time.sleep(3)

print("\n===== OVERALL =====")
print(f"Precision:       {tot_tp / tot_pred:.2f}")
print(f"Recall:          {tot_gold_hit / tot_gold:.2f}")
print(f"Status accuracy: {status_ok / tot_gold_hit:.2f}")
print(f"Avg faithfulness:{sum(faith_scores)/len(faith_scores):.2f}")