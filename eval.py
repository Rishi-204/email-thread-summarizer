import json
import time
from thread_parser import parse_thread, format_for_llm
from chunker import summarize_long
from verifier import faithfulness_report

labels = json.load(open("data/labels.json", encoding="utf-8"))


def norm_status(s: str) -> str:
    return "done" if s.strip().lower() in ("done", "completed", "complete") else "open"


def matches(pred, gold) -> bool:
    return (pred.owner.strip().lower() == gold["owner"].lower()
            and all(k in pred.task.lower() for k in gold["keywords"]))


def match_all(preds, gold):
    """One-to-one matching: each prediction can satisfy at most one gold item."""
    used, pairs = set(), {}
    for gi, g in enumerate(gold):
        for pi, p in enumerate(preds):
            if pi not in used and matches(p, g):
                used.add(pi)
                pairs[gi] = p
                break
    return pairs


rows = []
tot_pred = tot_gold = tot_tp = 0
status_ok = dl_total = dl_ok = 0
faith = []
failed = []
issues = []   # missed / extra items, for the failure analysis

for fname, gold in labels.items():
    try:
        msgs = parse_thread(open(f"data/{fname}", encoding="utf-8").read())
        result = summarize_long(msgs)
        rep = faithfulness_report(result, msgs, format_for_llm(msgs))
    except Exception as e:
        print(f"{fname}: FAILED ({str(e)[:80]})")
        failed.append(fname)
        continue

    preds = result.action_items
    pairs = match_all(preds, gold)
    tp = len(pairs)

    for gi, g in enumerate(gold):
        m = pairs.get(gi)
        if m:
            status_ok += norm_status(m.status) == g["status"]
        else:
            issues.append(f"{fname}: MISSED {g['owner']} {g['keywords']}")
        if "deadline" in g:
            dl_total += 1
            if m and g["deadline"] in m.deadline.lower():
                dl_ok += 1

    matched_preds = {id(p) for p in pairs.values()}
    for p in preds:
        if id(p) not in matched_preds:
            issues.append(f"{fname}: EXTRA {p.owner}: {p.task} [{p.status}]")

    prec = tp / len(preds) if preds else 1.0
    rec = tp / len(gold) if gold else 1.0
    faith.append(rep["faithfulness_score"])
    rows.append((fname, len(gold), len(preds), prec, rec, rep["faithfulness_score"]))

    print(f"{fname}: gold={len(gold)} pred={len(preds)} "
          f"P={prec:.2f} R={rec:.2f} F={rep['faithfulness_score']}")
    for p in preds:
        print(f"    - {p.owner}: {p.task} [{p.status}] ({p.deadline})")

    tot_pred += len(preds)
    tot_gold += len(gold)
    tot_tp += tp
    time.sleep(3)

precision = tot_tp / tot_pred if tot_pred else 0
recall = tot_tp / tot_gold if tot_gold else 0
f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
status_acc = status_ok / tot_tp if tot_tp else 0
dl_acc = dl_ok / dl_total if dl_total else 0
avg_faith = sum(faith) / len(faith) if faith else 0

print("\n===== OVERALL =====")
print(f"Threads evaluated: {len(rows)}/{len(labels)}  (failed: {failed or 'none'})")
print(f"Precision:         {precision:.2f}")
print(f"Recall:            {recall:.2f}")
print(f"F1:                {f1:.2f}")
print(f"Status accuracy:   {status_acc:.2f}")
print(f"Deadline accuracy: {dl_acc:.2f}")
print(f"Avg faithfulness:  {avg_faith:.2f}")

print("\n===== MISSED / EXTRA ITEMS =====")
print("\n".join(issues) if issues else "none")

with open("results.md", "w", encoding="utf-8") as f:
    f.write("# Evaluation results\n\n")
    f.write("| Metric | Value |\n|---|---|\n")
    f.write(f"| Threads evaluated | {len(rows)}/{len(labels)} |\n")
    f.write(f"| Gold action items | {tot_gold} |\n")
    f.write(f"| Precision | {precision:.2f} |\n")
    f.write(f"| Recall | {recall:.2f} |\n")
    f.write(f"| F1 | {f1:.2f} |\n")
    f.write(f"| Status accuracy | {status_acc:.2f} |\n")
    f.write(f"| Deadline accuracy | {dl_acc:.2f} |\n")
    f.write(f"| Avg faithfulness | {avg_faith:.2f} |\n\n")
    f.write("Matching is one-to-one: each predicted item can satisfy at most one gold item.\n\n")
    f.write("| Thread | Gold | Pred | Precision | Recall | Faithfulness |\n|---|---|---|---|---|---|\n")
    for r in rows:
        f.write(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]:.2f} | {r[4]:.2f} | {r[5]} |\n")
    f.write("\n## Missed / extra items\n\n")
    f.write("\n".join(f"- {i}" for i in issues) if issues else "None")
    f.write("\n")
print("\nSaved results.md")