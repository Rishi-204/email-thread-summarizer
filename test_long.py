from thread_parser import Message, format_for_llm
from chunker import summarize_long, thread_tokens
from verifier import faithfulness_report

fillers = ["Sounds good, thanks for the update.", "Noted, will keep an eye on it.",
           "Can we discuss this in the Monday sync?", "Looks fine to me."]
people = ["Alice", "Bob", "Carol", "Dave"]

msgs = [Message(i, people[i % 4], f"2026-10-{1 + i // 4:02d}", fillers[i % 4])
        for i in range(1, 61)]
msgs[2].body = "Bob, please prepare the vendor contract draft by 15 Oct."
msgs[10].body = "Carol, please book the venue for the offsite."
msgs[50].body = "The vendor contract draft is done and sent to legal. - Bob"

print(f"~{thread_tokens(msgs)} tokens")
# single_pass_limit=0 forces chunking; 400-token chunks give ~5 chunks
result = summarize_long(msgs, chunk_tokens=400, single_pass_limit=0)
print(result.model_dump_json(indent=2))

text = format_for_llm(msgs)
report = faithfulness_report(result, msgs, text)
print("\nQuote match:", report["quote_match"])
print("Faithfulness:", report["faithfulness_score"])
