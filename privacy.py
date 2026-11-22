import re
from dataclasses import replace
from thread_parser import Message

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"\+?\d[\d\s-]{8,}\d")
LEFTOVER = re.compile(r"\[(PERSON|EMAIL|PHONE)_\d+\]")


class Masker:
    """Stable placeholders: one real entity always gets the same placeholder,
    in every message and every chunk (one Masker per thread)."""

    def __init__(self):
        self.restore_map = {}   # placeholder -> original
        self._seen = {}         # (kind, original) -> placeholder
        self._count = {}
        self.names = []         # person names/aliases, longest first

    def _placeholder(self, kind, original):
        key = (kind, original)
        if key not in self._seen:
            self._count[kind] = self._count.get(kind, 0) + 1
            ph = f"[{kind}_{self._count[kind]}]"
            self._seen[key] = ph
            self.restore_map[ph] = original
        return self._seen[key]

    def register_people(self, people: dict):
        """people = {"Priya Sharma": ["Priya", "Sharma"], ...}
        A first/last name maps to the SAME placeholder as the full name,
        unless that token is shared by two different people."""
        owners = {}
        for full, aliases in people.items():
            for a in aliases:
                owners.setdefault(a.lower(), set()).add(full)
        for full, aliases in people.items():
            ph = self._placeholder("PERSON", full)
            self.names.append(full)
            for a in aliases:
                if len(owners[a.lower()]) == 1 and a != full:
                    self._seen[("PERSON", a)] = ph
                    self.names.append(a)
        self.names.sort(key=len, reverse=True)

    def mask_text(self, text: str, names=None) -> str:
        text = EMAIL.sub(lambda m: self._placeholder("EMAIL", m.group()), text)
        text = PHONE.sub(lambda m: self._placeholder("PHONE", m.group()), text)
        for n in self.names:
            text = re.sub(rf"\b{re.escape(n)}\b", self._seen[("PERSON", n)], text)
        return text

    def restore(self, text: str) -> str:
        for ph in sorted(self.restore_map, key=len, reverse=True):
            text = text.replace(ph, self.restore_map[ph])
        return text

    def restore_obj(self, obj):
        if isinstance(obj, str):
            return self.restore(obj)
        if isinstance(obj, list):
            return [self.restore_obj(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self.restore_obj(v) for k, v in obj.items()}
        return obj


def _people_from_senders(messages: list[Message]) -> dict:
    people = {}
    for m in messages:
        display = EMAIL.sub("", m.sender).replace("<", "").replace(">", "")
        display = display.strip().strip('"').strip()
        if not display or display.lower() == "unknown":
            continue
        parts = [p for p in re.split(r"[\s,]+", display) if len(p) > 2]
        people[display] = [p for p in parts if p != display]
    return people


def mask_messages(messages: list[Message]):
    masker = Masker()
    masker.register_people(_people_from_senders(messages))
    masked = [
        replace(m,
                sender=masker.mask_text(m.sender),
                body=masker.mask_text(m.body))
        for m in messages
    ]
    return masked, masker


def has_leftover_placeholders(text: str) -> bool:
    return bool(LEFTOVER.search(text))
