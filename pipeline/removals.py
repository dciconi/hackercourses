"""Comments their authors asked to take down. build.py skips them on every build, so a later
data refresh can't bring them back.

removals.txt (repo root), one entry per line:
    41709040        an HN comment id (the number in news.ycombinator.com/item?id=...)
    user:pg         every comment by that HN username
    reddit:abc12    a Reddit comment id (the last part of a comment permalink); "t1_" prefix optional
    reddit-user:pg  every comment by that Reddit username
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
        low = entry.lower()
        if low.startswith("reddit-user:"):
            name = low[12:].strip()
            if not re.fullmatch(r"[\w-]+", name):
                raise ValueError(f"removals.txt: can't read {line!r} (use reddit-user:name)")
            users.add(("reddit", name))
        elif low.startswith("reddit:"):
            m = re.fullmatch(r"(?:t1_)?([a-z0-9]+)", low[7:].strip())
            if not m:
                raise ValueError(f"removals.txt: can't read {line!r} (use reddit:<base36 comment id>)")
            ids.add("t1_" + m.group(1))
        elif low.startswith("user:"):
            users.add(("hn", low[5:].strip()))
        elif re.fullmatch(r"\d+", entry):
            ids.add(int(entry))
        else:
            raise ValueError(f"removals.txt: can't read {line!r} (use a comment id, user:name, "
                             "reddit:id or reddit-user:name)")
    return ids, users


def removed(item, ids, users):
    return item["id"] in ids or (item.get("src", "hn"), (item.get("by") or "").lower()) in users
