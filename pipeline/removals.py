"""Comments their authors asked to take down. build.py skips them on every build, so a later
data refresh can't bring them back.

removals.txt (repo root), one entry per line:
    41709040        an HN comment id (the number in news.ycombinator.com/item?id=...)
    user:pg         every comment by that HN username
    # anything after a hash is a note
"""

import re

from classify import ROOT

FILE = ROOT / "removals.txt"


def load(path=None):
    path = path or FILE
    ids, users = set(), set()
    if not path.exists():
        return ids, users
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if not entry:
            continue
        if entry.lower().startswith("user:"):
            users.add(entry[5:].strip().lower())
        elif re.fullmatch(r"\d+", entry):
            ids.add(int(entry))
        else:
            raise ValueError(f"removals.txt: can't read {line!r} (use a comment id or user:name)")
    return ids, users


def removed(item, ids, users):
    return item["id"] in ids or (item.get("by") or "").lower() in users
