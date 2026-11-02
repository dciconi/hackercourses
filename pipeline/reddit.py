"""Normalize Reddit archive comments into the same row shape classify.py reads for HN."""

import html
import re

import fetch
from sources import SUBREDDITS

# Reddit-only course providers, beyond the generic HN prefilter and rule lists.
REDDIT_HOSTS = (
    "academy.hubspot.com", "skillshop.withgoogle.com", "learndigital.withgoogle.com", "grow.google",
    "maven.com", "teachable.com", "kajabi.com", "podia.com", "thinkific.com", "skillshare.com",
    "domestika.org", "reforge.com",
)
REDDIT_NAMED = (
    r"hubspot academy|google skillshop|digital garage|google (ads|analytics) certification|maven|"
    r"reforge|skillshare|domestika|building a second brain|startup school|linkedin learning|masterclass"
)
REDDIT_SPAM = re.compile(
    r"check (out )?my (profile|bio)|link in (my )?(bio|profile)|\bpm me\b|\bjoin my\b|"
    r"use my (link|code)|gumroad\.com/l/|stan\.store|whop\.com",
    re.I,
)
PREFILTER = re.compile(
    "|".join([fetch.PREFILTER.pattern, REDDIT_NAMED, *(re.escape(h) for h in REDDIT_HOSTS)]), re.I
)

_SUBS = {s.lower() for s in SUBREDDITS}
_GONE = ("[deleted]", "[removed]")
_MD_LINK = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")
_BARE_URL = re.compile(r"https?://[^\s)\]>]+")


def to_text(md: str) -> tuple[str, list[str]]:
    """Plain text plus every URL found, in order; `>` quote lines are kept."""
    md = html.unescape(md)
    links = []

    def keep(m):
        links.append(m.group(2))
        return m.group(1)

    text = _MD_LINK.sub(keep, md)
    links += _BARE_URL.findall(text)
    return text, links


def candidate(raw: dict) -> dict | None:
    body, author = raw.get("body") or "", raw.get("author") or ""
    sub = raw.get("subreddit") or ""
    if body.strip() in _GONE or author in _GONE or not author:
        return None
    if sub.lower() not in _SUBS or not PREFILTER.search(body):
        return None
    created = int(raw["created_utc"])
    seen = raw.get("retrieved_on") or raw.get("retrieved_utc")
    return {"id": f"t1_{raw['id']}", "by": author, "time": created, "text": body, "src": "reddit",
            "sub": sub, "ups": int(raw.get("score") or 0), "age": int(seen) - created if seen else None,
            "thread": raw.get("link_id")}


def permalink(item: dict) -> str:
    return f"https://www.reddit.com/r/{item['sub']}/comments/{item['thread'][3:]}/_/{item['id'][3:]}/"
