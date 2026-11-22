from thread_parser import Message, format_for_llm
from chunker import summarize_long, thread_tokens

people = ["Alice", "Bob", "Carol", "Dave"]
msgs = [Message(i, people[i % 4], "2026-10-01", "Sounds good, noted.") for i in range(1, 201)]
msgs[4].body = "Bob, please prepare the vendor contract by 15 Oct."
msgs[60].body = "Carol, please book the venue for the offsite."
msgs[120].body = "Dave, please send the invoice to finance."
msgs[190].body = "The vendor contract is done and sent. - Bob"

print(f"~{thread_tokens(msgs)} tokens")
single = summarize_long(msgs, single_pass_limit=10**9)                  # always one call
chunked = summarize_long(msgs, chunk_tokens=1500, single_pass_limit=0)  # always chunked

for name, r in [("SINGLE PASS", single), ("CHUNKED", chunked)]:
    print(f"\n{name}: {len(r.action_items)} items")
    for a in r.action_items:
        print(f"  - {a.owner}: {a.task} [{a.status}] ({a.deadline})")
