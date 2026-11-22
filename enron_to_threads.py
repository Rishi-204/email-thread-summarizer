"""Build long test threads from the Enron maildir (CMU, 2015-05-07 version).

Usage (from the project folder):
    python enron_to_threads.py path/to/maildir --count 5

Writes data/enron_01.txt ... in our thread format. Real people are in this data:
keep these files LOCAL (they are gitignored) and run the tools with PII masking on.
"""
import argparse
import os
import re
from collections import defaultdict
from email import message_from_binary_file, policy
from email.utils import parsedate_to_datetime

ap = argparse.ArgumentParser()
ap.add_argument("maildir")
ap.add_argument("--max-users", type=int, default=40)
ap.add_argument("--min-msgs", type=int, default=8)
ap.add_argument("--max-msgs", type=int, default=45)
ap.add_argument("--min-senders", type=int, default=3)
ap.add_argument("--count", type=int, default=5)
ap.add_argument("--out", default="data")
args = ap.parse_args()

SENT = {"sent_mail", "_sent_mail", "sent", "sent_items"}
CUT = re.compile(r"^\s*-{2,}\s*(original message|forwarded by).*", re.I)
PREFIX = re.compile(r"^\s*((re|fw|fwd)\s*:\s*)+", re.I)


def clean(body: str) -> str:
    lines = []
    for line in body.splitlines():
        if CUT.match(line):
            break
        if line.strip().startswith(">"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()[:2000]


def body_of(msg) -> str:
    try:
        part = msg.get_body(preferencelist=("plain",))
        if part is not None:
            return part.get_content()
    except Exception:
        pass
    payload = msg.get_payload(decode=True)
    return payload.decode("utf-8", "ignore") if payload else ""


threads = defaultdict(dict)   # subject -> {dedupe key: (datetime, name, addr, body)}
users = sorted(os.listdir(args.maildir))[:args.max_users]
for user in users:
    upath = os.path.join(args.maildir, user)
    if not os.path.isdir(upath):
        continue
    for folder in os.listdir(upath):
        if folder.lower() not in SENT:
            continue
        for root, _, files in os.walk(os.path.join(upath, folder)):
            for fn in files:
                try:
                    with open(os.path.join(root, fn), "rb") as fh:
                        msg = message_from_binary_file(fh, policy=policy.default)
                    subject = PREFIX.sub("", str(msg["Subject"] or "")).strip().lower()
                    if len(subject) < 4 or subject == "(no subject)":
                        continue
                    when = parsedate_to_datetime(str(msg["Date"]))
                    body = clean(body_of(msg))
                    if not body:
                        continue
                    addr = str(msg["From"] or "unknown@enron.com")
                    name = re.sub(r"<.*?>", "", str(msg["X-From"] or "")).strip() \
                        or addr.split("@")[0]
                    key = str(msg["Message-ID"] or (when, addr, body[:60]))
                    threads[subject][key] = (when, name, addr, body)
                except Exception:
                    continue

candidates = []
for subject, msgs in threads.items():
    n = len(msgs)
    senders = {v[2] for v in msgs.values()}
    if args.min_msgs <= n <= args.max_msgs and len(senders) >= args.min_senders:
        candidates.append((n, subject, sorted(msgs.values(), key=lambda v: v[0])))
candidates.sort(key=lambda c: -c[0])

os.makedirs(args.out, exist_ok=True)
for i, (n, subject, msgs) in enumerate(candidates[:args.count], 1):
    blocks = [f"From: {name} <{addr}>\nDate: {when:%Y-%m-%d}\n\n{body}"
              for when, name, addr, body in msgs]
    path = os.path.join(args.out, f"enron_{i:02d}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n======\n".join(blocks) + "\n")
    print(f"{path}: {n} messages, subject: {subject[:60]}")
if not candidates:
    print("No threads matched. Try --max-users 150 or --min-msgs 6.")
