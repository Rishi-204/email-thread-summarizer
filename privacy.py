import re
from dataclasses import replace
from thread_parser import Message

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\+?\d[\d\s-]{8,}\d")

class Masker:
    def __init__(self):
        self.restore_map = {}   # placeholder -> original
        self._seen = {}         # (kind, original) -> placeholder
        self._count = {}

    def _placeholder(self, kind, original):
        key = (kind, original)
        if key not in self._seen:
            self._count[kind] = self._count.get(kind, 0) + 1
            ph = f"[{kind}_{self._count[kind]}]"
            self._seen[key] = ph
            self.restore_map[ph] = original
        return self._seen[key]

    def mask_text(self, text: str, names: list[str]) -> str:
        text = EMAIL.sub(lambda m: self._placeholder("EMAIL", m.group()), text)
        text = PHONE.sub(lambda m: self._placeholder("PHONE", m.group()), text)
        for n in names:   # longest first
            text = re.sub(rf"\b{re.escape(n)}\b", self._placeholder("PERSON", n), text)
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

def _names_from_senders(messages: list[Message]) -> list[str]:
    names = set()
    for m in messages:
        display = EMAIL.sub("", m.sender).replace("<", "").replace(">", "").strip()
        if display:
            names.add(display)
            names.update(p for p in display.split() if len(p) > 2)
    return sorted(names, key=len, reverse=True)

def mask_messages(messages: list[Message]):
    masker = Masker()
    names = _names_from_senders(messages)
    masked = [
        replace(m,
                sender=masker.mask_text(m.sender, names),
                body=masker.mask_text(m.body, names))
        for m in messages
    ]
    return masked, masker