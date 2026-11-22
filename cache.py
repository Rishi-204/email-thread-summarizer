import hashlib, json, os

CACHE_DIR = "cache"

def make_key(text: str, mask: bool, max_chars: int) -> str:
    raw = f"{mask}|{max_chars}|{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]

def load(key: str):
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None

def save(key: str, data: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(os.path.join(CACHE_DIR, f"{key}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)