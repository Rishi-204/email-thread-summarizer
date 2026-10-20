from thread_parser import Message, format_for_llm
from chunker import summarize_long
from verifier import faithfulness_report

fillers = ["Sounds good, thanks for the update.", "Noted, will keep an eye on it.",
           "Can we discuss this in the Monday sync?", "Looks fine to me."]
people = ["Alice", "Bob", "Carol", "Dave"]

msgs = [Message(i, people[i % 4], f"2026-10-{1 + i // 4:02d}", fillers[i % 4])
        for i in range(1, 61)]
msgs[2].body = "Bob, please prepare the vendor contract draft by 15 Oct."
msgs[10].body = "Carol, please book the venue for the offsite."
msgs[50].body = "The vendor contract draft is done and sent to legal. - Bob"

result = summarize_long(msgs, max_chars=1500)   # small value forces ~5 chunks
print(result.model_dump_json(indent=2))

text = format_for_llm(msgs)
report = faithfulness_report(result, msgs, text)
print("\nQuote match:", report["quote_match"])
print("Faithfulness:", report["faithfulness_score"])