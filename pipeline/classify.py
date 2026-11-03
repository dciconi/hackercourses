"""Filter candidates down to non-spam comments that recommend a course, and assign topics.

Rule-based on purpose: deterministic, auditable, and needs no API key.
Reads data/candidates.jsonl, writes data/pool.json and data/courses.json
(applying data/llm_labels.jsonl from review.py when present).
"""

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from functools import partial
from multiprocessing import Pool
from pathlib import Path
from urllib.parse import urlparse

import reddit
import sources

ROOT = Path(__file__).resolve().parent.parent
_P = sources.paths("hn")
SRC = _P.candidates
OUT_JSON = _P.courses
POOL = _P.pool  # rule matches handed to review.py
LABELS = _P.labels  # written by review.py
OUT_JS = ROOT / "site" / "data.js"

# --- text cleanup -----------------------------------------------------------

HREF = re.compile(r'<a\s[^>]*href="([^"]+)"', re.I)
TAG = re.compile(r"<[^>]+>")
QUOTE = re.compile(r"(^|\n)\s*>[^\n]*", re.M)  # HN quoting convention


def to_text(raw):
    links = [html.unescape(h) for h in HREF.findall(raw)]
    t = raw.replace("<p>", "\n\n")
    t = html.unescape(TAG.sub("", t))
    # The source dump lost curly quotes to U+FFFD; nearly all of them were apostrophes.
    return t.replace("�", "'").strip(), links


# --- "course" that is not a course --------------------------------------------

NOT_A_COURSE = re.compile(
    r"\b(of|in due|matter of|par for the|over the|in the|during the|stay(ed|ing)? the|"
    r"change(d|s)? (of )?|alter(ed)? |set (a |the )?|chart(ed|ing)? (a |the )?|"
    r"collision|golf|race|obstacle|main|first|second|third|natural|due|middle) course\b|"
    r"\bcourse(s)? (of action|of events|of history|of treatment|of time|correct\w*|of (a|the|my|his|her|their|its|our))\b|"
    r"\bcourse of\b|\bof course\b|"
    r"\b(first|second|world|middle|working|upper|lower|ruling|business|economy|top|own|same|different|"
    r"whole|new|base|abstract|type|utility|asset|attack|creative|leisure|chattering|managerial|professional) class(es)?\b|"
    r"\bclass(es)? (action|warfare|struggle|of|system|hierarchy|name|names|method|methods|instance|"
    r"variable|variables|definition|hierarchies|inheritance|file|files|loader|path|based|component|"
    r"components|act|consciousness|divide|mobility|traitor)\b",
    re.I,
)

# --- recommendation signals ---------------------------------------------------

COURSE_WORD = r"\b(courses?|moocs?|class(es)?|lectures?|specialization|nanodegree|lecture series)\b"
PRAISE = (r"(great|excellent|fantastic|amazing|wonderful|superb|outstanding|brilliant|best|favou?rite|"
          r"awesome|phenomenal|incredible|terrific|top[- ]notch|life[- ]changing|eye[- ]opening|"
          r"very good|really good|enjoyable|mind[- ]blowing)")
RECOMMEND = re.compile(
    r"\brecommend(ed|ing|s|ation)?\b|\bcheck(ing)? out\b|\bsuggest\b|\bmust[- ]take\b|"
    r"\bworth (taking|it|your time|doing|a look|checking|watching)\b|"
    r"\b(take|try|do|look (at|into)|start with|go through|enroll in|sign up for)\b[^.\n]{0,60}" + COURSE_WORD + r"|"
    r"\b" + PRAISE + r"\b[^.\n]{0,40}" + COURSE_WORD + r"|"
    + COURSE_WORD + r"[^.\n]{0,50}\b(is|was|are|were) (really |absolutely |just )?(" + PRAISE + r"|the best|worth)\b|"
    r"\bi (loved|enjoyed|learned (a lot|so much))\b[^.\n]{0,60}" + COURSE_WORD,
    re.I,
)
NEGATIVE = re.compile(
    r"\b(don'?t|do not|wouldn'?t|would not|can'?t|cannot|never|not sure (i'?d|i would)) (really )?recommend|"
    r"\bavoid\b|\bwaste of (time|money)\b|\b(terrible|awful|useless|overrated|worst)\b[^.\n]{0,30}"
    + COURSE_WORD,
    re.I,
)
# A comment must point at a specific course, not courses in general.
COURSE_HOSTS = (
    "coursera.org", "edx.org", "udacity.com", "udemy.com", "khanacademy.org", "ocw.mit.edu",
    "online.stanford.edu", "see.stanford.edu", "cs50.harvard.edu", "fast.ai", "course.fast.ai",
    "nand2tetris.org", "pluralsight.com", "egghead.io", "frontendmasters.com", "classcentral.com",
    "futurelearn.com", "theodinproject.com", "freecodecamp.org", "missing.csail.mit.edu",
    "cs231n", "cs229", "brilliant.org", "datacamp.com", "codecademy.com", "teachyourselfcs.com",
    "youtube.com/playlist", "youtube.com/course", "deeplearning.ai", "huggingface.co/course",
    "huggingface.co/learn", "openlearning", "open.edu", "academicearth", "linkedin.com/learning",
    "lynda.com", "masterclass.com", "greatcourses", "wondrium.com", "pll.harvard.edu",
)
NAMED_COURSE = re.compile(
    r"(?i:\b(coursera|edx|udacity|udemy|khan academy|mit ocw|opencourseware|nand2tetris|fast\.ai|"
    r"pluralsight|egghead|frontend masters|cs ?50|cs ?61a|cs ?231n|cs ?229|cs ?224n|cs ?106[ab]|"
    r"6\.0?0[0-9]\w*|6\.8[0-9]{2}|18\.06|18\.01|sicp|andrew ng|odin project|freecodecamp|"
    r"missing semester|deeplearning\.ai|great courses|wondrium|brilliant\.org|datacamp|codecademy|"
    r"stanford|harvard|berkeley|caltech|cmu|princeton|mit)\b)|"
    r"\b(CS|EE|CSE|COS|CMSC|ECE|MATH|STAT|PHYS) ?\d{2,4}[A-Z]?\b|"  # course codes like CS 61A
    r"\b1[0-9]-\d{3}\b|"  # CMU style, 15-213
    r"\b[A-Z][a-z]+(?:'s|’s) (?:\w+ ){0,3}(?i:" + COURSE_WORD + r")|"  # Strang's linear algebra course
    r"[\"“][^\"”\n]{4,80}[\"”] (?i:" + COURSE_WORD + r")",  # the "Learning How to Learn" course
)

REDDIT_NAMED_RX = re.compile(r"(?i:\b(" + reddit.REDDIT_NAMED + r")\b)")

# --- spam -------------------------------------------------------------------

SPAM = re.compile(
    r"couponcode=|coupon code|promo code|discount code|use code\b|\b\d{2,3}% off\b|"
    r"\baffiliate\b|[?&](ref|aff|affid|ranmid|ranEAID|siteID)=|enroll (now|today)|limited time|"
    r"\bfree certificate\b|bit\.ly/|tinyurl\.com/|whatsapp|telegram\.me|\bdm me\b|"
    r"\b(my|our) (new |online |video )?(courses?|bootcamps?|class(es)?)\b|"
    r"\bi('ve| have)? (made|created|built|launched|teach|wrote|recorded) (a|an|this|my)\b",
    re.I,
)

# --- topics -----------------------------------------------------------------

TOPICS = [
    ("Machine Learning & AI", r"machine learning|deep learning|neural ?net|\bml\b|\bai\b|andrew ng|fast\.ai|"
     r"cs ?229|cs ?231n|cs ?224n|deeplearning\.ai|\bnlp\b|reinforcement learning|computer vision|\bllms?\b|"
     r"transformer|pytorch|tensorflow|data scien|kaggle|hinton|karpathy|probabilistic graphical"),
    ("Algorithms & Data Structures", r"algorithm|data structure|sedgewick|cos ?226|roughgarden|skiena|leetcode|"
     r"dynamic programming|graph theory|competitive programming|6\.006|6\.046|complexity"),
    ("CS Fundamentals & Systems", r"nand2tetris|computer architecture|operating system|compiler|"
     r"\bos\b|cs ?61[abc]|15-213|systems programming|computer systems|cs ?50\b|missing semester|"
     r"sicp|structure and interpretation|computation|automata|distributed system|6\.824|6\.828|"
     r"networking|computer network|\bunix\b|\blinux\b|assembly|low[- ]level|teach ?yourself ?cs|crafting interpreters"),
    ("Mathematics", r"linear algebra|calculus|statistics|probability|\bmath|strang|18\.06|discrete math|"
     r"real analysis|abstract algebra|differential equation|number theory|3blue1brown|topology|"
     r"category theory|proof|khan academy"),
    ("Programming Languages", r"haskell|scala|lisp|scheme|clojure|racket|\bocaml\b|erlang|elixir|"
     r"\brust\b|\bgolang\b|\bgo course|functional programming|programming languages|odersky|"
     r"dan grossman|\bc\+\+|\bjava\b|python|javascript|typescript|ruby|prolog|type theory|\bsml\b"),
    ("Web & Mobile Development", r"\bweb dev|frontend|front-end|backend|back-end|full ?stack|react(js)?\b|"
     r"angular|\bvue\b|node\.?js|rails|django|flask|\bcss\b|\bhtml\b|ios dev|android|swift|"
     r"odin project|freecodecamp|frontend masters|egghead|wes bos|mobile app"),
    ("Databases & Data Engineering", r"database|\bsql\b|postgres|cmu 15-445|15-445|data engineering|"
     r"spark|hadoop|big data|data warehouse|nosql|query optim"),
    ("Security & Cryptography", r"security|cryptograph|crypto i\b|dan boneh|hacking|penetration|"
     r"exploit|reverse engineer|malware|\bctf\b|infosec"),
    ("Science & Engineering", r"physics|chemistry|biology|neuroscience|electr(on)?ic|circuits|"
     r"signal processing|control theory|robotics|quantum|astronomy|genetics|mechanical|"
     r"6\.002|6\.003|embedded|fpga|verilog|hardware design|medicine|anatomy"),
    ("Productivity & Personal Development", r"productivity|habit|procrastinat|time management|discipline|focus|"
     r"note[- ]taking|second brain|\bpkm|zettelkasten|obsidian|notion|journaling|bujo|self[- ]improvement|"
     r"personal development|deep work"),
    ("Marketing & Growth", r"marketing|\bseo\b|\bppc\b|google ads|facebook ads|meta ads|copywriting|"
     r"email (marketing|campaign)|growth|social media|content strategy|brand|funnel|conversion"),
    ("Business, Finance & Economics", r"econom|finance|financial|accounting|startup|entrepreneur|"
     r"business|management|negotiation|investing|valuation|venture|game theory|"
     r"how to start a startup|strategy"),
    ("Design & Creative", r"\bdesign|drawing|music|guitar|piano|photograph|writing|film|"
     r"animation|typography|\bux\b|\bui\b|art history|painting|game dev|creative"),
    ("Humanities & Social Science", r"philosoph|history|psycholog|sociolog|literature|"
     r"political|ethics|religio|justice|sandel|linguistic|anthropolog|law\b|learning how to learn|"
     r"language learning|spanish|french|german|japanese|chinese|mandarin|latin|greek"),
]
TOPICS = [(name, re.compile(r"\b(?:" + rx + ")", re.I)) for name, rx in TOPICS]
OTHER = "General Learning"


def topic_of(text, links):
    hay = text + " " + " ".join(links)
    scores = {name: len(rx.findall(hay)) for name, rx in TOPICS}
    best = max(scores, key=scores.get)
    return best if scores[best] else OTHER


EDU_COURSE_PATH = re.compile(r"\.edu/.*\b(courses?|class(es)?|lectures?|~?cs\d+)\b", re.I)
COURSE_WORD_RX = re.compile(COURSE_WORD, re.I)
SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")


def course_links(links, hosts=COURSE_HOSTS):
    out = []
    for u in links:
        low = u.lower()
        if any(h in low for h in hosts) or EDU_COURSE_PATH.search(low):
            out.append(u)
    return list(dict.fromkeys(out))[:5]


def recommends_course(scrubbed, hosts=COURSE_HOSTS, named=(NAMED_COURSE,)):
    """A recommendation and a specific course must sit in the same or adjacent sentences."""
    sents = [s for s in SENTENCES.split(scrubbed) if s.strip()]
    for i in range(len(sents)):
        window = " ".join(sents[i:i + 2])
        if not RECOMMEND.search(sents[i]) and not RECOMMEND.search(window):
            continue
        low = window.lower()
        course_url = any(h in low for h in hosts) or EDU_COURSE_PATH.search(low)
        if (COURSE_WORD_RX.search(window) or course_url) and (any(n.search(window) for n in named) or course_url):
            return True
    return False


def classify(row, source="hn"):
    is_reddit = source == "reddit"
    text, links = reddit.to_text(row["text"]) if is_reddit else to_text(row["text"])
    spam = (SPAM, reddit.REDDIT_SPAM) if is_reddit else (SPAM,)
    hosts = COURSE_HOSTS + reddit.REDDIT_HOSTS if is_reddit else COURSE_HOSTS
    named = (NAMED_COURSE, REDDIT_NAMED_RX) if is_reddit else (NAMED_COURSE,)
    if len(text) < 40 or len(text) > 6000:
        return None, "length"
    if any(rx.search(row["text"]) for rx in spam):
        return None, "spam"
    # Judge only the author's own words, not what they are quoting.
    own = QUOTE.sub("\n", text)
    scrubbed = NOT_A_COURSE.sub(" ", own)
    clinks = course_links(links, hosts)
    if not COURSE_WORD_RX.search(scrubbed) and not clinks:
        return None, "not-a-course"
    if NEGATIVE.search(scrubbed):
        return None, "negative"
    if not recommends_course(scrubbed, hosts, named):
        return None, "no-recommendation"
    item = {
        "id": row["id"],
        "by": row["by"],
        "time": row["time"],
        "text": text,
        "links": clinks,
        "topic": topic_of(own, clinks),
        "score": confidence(scrubbed, clinks, named),
    }
    if is_reddit:
        item.update({k: row.get(k) for k in ("src", "sub", "ups", "age", "thread")})
    return item, "kept"


def confidence(scrubbed, clinks, named=(NAMED_COURSE,)):
    """0-5, used for ordering: explicit endorsement of a linked, named course ranks first."""
    s = 0
    s += 2 if re.search(r"\b(highly|strongly|definitely) recommend|\brecommend\b", scrubbed, re.I) else 0
    s += 1 if re.search(PRAISE, scrubbed, re.I) else 0
    s += 1 if clinks else 0
    s += 1 if any(n.search(scrubbed) for n in named) else 0
    return s


def apply_labels(pool, reasons, LABELS=LABELS):
    """Second pass from review.py: the model's verdict decides inclusion, topic and course names."""
    labels = {}
    with LABELS.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            labels[row["id"]] = row
    out = []
    for it in pool:
        lab = labels.get(it["id"])
        if lab is None:
            # Not reviewed yet: fall back to the rule threshold.
            reasons["unreviewed"] += 1
            if it["score"] >= 2:
                out.append(it)
            continue
        if lab["spam_or_self_promotion"]:
            reasons["llm-spam"] += 1
        elif not lab["recommends_course"]:
            reasons["llm-not-a-recommendation"] += 1
        else:
            it["topic"] = lab["topic"]
            it["courses"] = lab["courses"]
            out.append(it)
    return out


SUBREDDITS_LOWER = {s.lower() for s in sources.SUBREDDITS}


def classify_line(line, source="hn"):
    row = json.loads(line)
    if source == "reddit" and (row.get("sub") or "").lower() not in SUBREDDITS_LOWER:
        return None, "dropped-subreddit"
    if not row.get("text") or not row.get("by"):
        return None, "empty"
    return classify(row, source)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=sources.SOURCES, default="hn")
    ap.add_argument("candidates", nargs="?", type=Path, help="override the candidates file")
    args = ap.parse_args()
    p = sources.paths(args.source)
    POOL, LABELS, OUT_JSON = p.pool, p.labels, p.courses
    src = args.candidates or p.candidates
    reasons = Counter()
    kept = []
    seen_text = set()
    with src.open(encoding="utf-8") as f, Pool() as pool:
        for item, why in pool.imap(partial(classify_line, source=args.source), f, chunksize=2000):
            reasons[why] += 1
            if not item:
                continue
            key = re.sub(r"\W+", "", item["text"].lower())[:300]
            if key in seen_text:  # copy-pasted comments
                reasons["duplicate"] += 1
                reasons["kept"] -= 1
                continue
            seen_text.add(key)
            kept.append(item)

    # Accounts that drop the same course link over and over are promoting, not recommending.
    per_author_host = Counter()
    for it in kept:
        for host in {urlparse(u).netloc.removeprefix("www.") + urlparse(u).path.rstrip("/") for u in it["links"]}:
            per_author_host[(it["by"], host)] += 1
    promoters = {a for (a, _), n in per_author_host.items() if n >= 5}
    before = len(kept)
    kept = [it for it in kept if it["by"] not in promoters]
    reasons["repeat-promoter"] = before - len(kept)
    POOL.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")
    reasons["rule-pool"] = len(kept)
    del reasons["kept"]

    kept = apply_labels(kept, reasons, LABELS) if LABELS.exists() else [it for it in kept if it["score"] >= 2]
    reasons["kept"] = len(kept)
    kept.sort(key=lambda it: (-it["score"], -it["time"]))
    by_topic = defaultdict(int)
    for it in kept:
        by_topic[it["topic"]] += 1

    # site/data.js is assembled later by build.py from the canonical courses.
    OUT_JSON.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")
    order = [name for name, _ in TOPICS] + [OTHER]
    for k, v in reasons.most_common():
        print(f"{k:>20}: {v}")
    print()
    for n in order:
        print(f"{n:>32}: {by_topic[n]}")


if __name__ == "__main__":
    main()
