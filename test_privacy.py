"""Checks that placeholders are stable and nothing leaks. No API calls."""
from thread_parser import Message
from privacy import mask_messages, has_leftover_placeholders

msgs = [
    Message(1, "Priya Sharma <priya@x.com>", "d", "Rahul, please call +91 98765 43210 about the invoice."),
    Message(2, "Rahul Verma <rahul@x.com>", "d", "Priya, I will call. Mail me at rahul@x.com."),
    Message(3, "Priya Sharma <priya@x.com>", "d", "Thanks Rahul."),
]
masked, masker = mask_messages(msgs)
for m in masked:
    print(m.sender, "|", m.body)

joined = " ".join(m.sender + " " + m.body for m in masked)

# 1. no real identifier is sent to the API
for real in ["Priya", "Rahul", "Sharma", "Verma", "priya@x.com", "rahul@x.com", "98765"]:
    assert real not in joined, f"LEAK: {real}"

# 2. the same person gets the same placeholder in every message
assert masked[0].body.split()[0].rstrip(",") == masked[1].sender.split()[0], "inconsistent"
assert masked[2].body.split()[1].rstrip(".") == masked[1].sender.split()[0], "inconsistent"

# 3. restoring brings the real values back and leaves no placeholder behind
restored = masker.restore(joined)
assert not has_leftover_placeholders(restored), "placeholder leaked into output"
assert "Rahul" in restored and "98765" in restored

print("\nAll privacy checks passed.")
