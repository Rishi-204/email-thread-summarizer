from thread_parser import Message, format_for_llm
from extractor import extract
from chunker import summarize_long

people = ["Alice", "Bob", "Carol", "Dave"]
msgs = [Message(i, people[i % 4], "2026-10-01", "Sounds good, noted.") for i in range(1, 201)]
msgs[4].body = "Bob, please prepare the vendor contract by 15 Oct."
msgs[60].body = "Carol, please book the venue for the offsite."
msgs[120].body = "Dave, please send the invoice to finance."
msgs[190].body = "The vendor contract is done and sent. - Bob"

single = extract(format_for_llm(msgs))
chunked = summarize_long(msgs, max_chars=4000)

for name, r in [("SINGLE PASS", single), ("CHUNKED", chunked)]:
    print(f"\n{name}: {len(r.action_items)} items")
    for a in r.action_items:
        print(f"  - {a.owner}: {a.task} [{a.status}]")