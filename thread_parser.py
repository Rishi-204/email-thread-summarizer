import re
from dataclasses import dataclass

@dataclass
class Message:
    id: int
    sender: str
    date: str
    body: str

SIG_PATTERNS = [r"^--\s*$", r"^Sent from my", r"^Regards,?$", r"^Best,?$", r"^Thanks,?$"]

def clean_body(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.strip().startswith(">"):          # quoted reply
            continue
        if re.match(r"^On .+ wrote:$", line.strip()):
            break                                  # rest is quoted history
        if any(re.match(p, line.strip(), re.I) for p in SIG_PATTERNS):
            break                                  # signature starts
        lines.append(line)
    return "\n".join(lines).strip()

def parse_thread(raw: str) -> list[Message]:
    """Messages separated by a line of ====== . Each starts with:
    From: ...
    Date: ...
    <blank line>
    body
    """
    messages = []
    for i, block in enumerate(re.split(r"\n={3,}\n", raw.strip())):
        sender = re.search(r"^From:\s*(.+)$", block, re.M)
        date = re.search(r"^Date:\s*(.+)$", block, re.M)
        parts = re.split(r"\n\s*\n", block, maxsplit=1)
        body = parts[1] if len(parts) > 1 else block
        messages.append(Message(
            id=i + 1,
            sender=sender.group(1).strip() if sender else "Unknown",
            date=date.group(1).strip() if date else "",
            body=clean_body(body),
        ))
    return messages

def format_for_llm(messages: list[Message]) -> str:
    return "\n\n".join(
        f"[MSG {m.id}] From: {m.sender} | Date: {m.date}\n{m.body}" for m in messages
    )