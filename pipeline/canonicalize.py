"""Merge the many spellings of each course into one canonical course.

1. Deterministic pre-merge: same normalized title within the same provider family.
2. LLM pass, most-mentioned first: each pre-merged name is either matched to a course
   already in the catalog or added as a new one. The catalog grows as it goes, so
   later (rarer) spellings can attach to the popular canonical entries.

Writes data/catalog.json: {"courses": [{id, name, provider, origin?}], "aliases": {"name|provider": id}}.
The catalog is shared by both sources (--source hn|reddit); entries record the source that created
them in "origin" (missing means hn).
Resumable: aliases already mapped are kept.
"""

import argparse
import json
import re
from collections import Counter, defaultdict

from llm import HAIKU, SONNET, api_key, structured
from sources import ROOT, SOURCES, paths

CATALOG = ROOT / "data" / "catalog.json"
BATCH = 80
MODEL = HAIKU
DEDUPE_MODEL = SONNET  # one call over the whole catalog; worth the stronger model

PROVIDER_FAMILIES = [
    ("Coursera", r"coursera"), ("edX", r"\bedx\b"), ("Udacity", r"udacity"), ("Udemy", r"udemy"),
    ("MIT OCW", r"\bmit\b|opencourseware|\bocw\b"), ("Stanford", r"stanford"), ("Harvard", r"harvard"),
    ("UC Berkeley", r"berkeley"), ("Carnegie Mellon", r"carnegie|\bcmu\b"), ("Caltech", r"caltech"),
    ("fast.ai", r"fast\.ai"), ("Khan Academy", r"khan"), ("The Great Courses", r"great courses|wondrium|teaching company"),
    ("YouTube", r"youtube"), ("nand2tetris", r"nand2tetris"), ("Pluralsight", r"pluralsight"),
]


def family(provider):
    for fam, rx in PROVIDER_FAMILIES:
        if re.search(rx, provider or "", re.I):
            return fam
    return (provider or "").strip()


def norm(name):
    n = name.lower()
    # Asides often name the instructor, which tells courses apart; only drop run dates.
    n = re.sub(r"\b(spring|summer|fall|autumn|winter)?\s*(19|20)\d\d\b", " ", n)
    n = re.sub(r"^(the|a|an)\s+", "", n)
    n = re.sub(r"[^\w.]+", " ", n)
    n = re.sub(r"\b(course|class|mooc|online|lectures?|video|series)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def alias_key(c):
    return f"{c['name']}|{c['provider']}"


# --- merge vetoes ----------------------------------------------------------
# The model sometimes merges sequels or a MOOC into the campus course it grew out of.
# These cheap checks overrule it.

MOOC_PLATFORMS = {"Coursera", "edX", "Udacity", "Udemy", "Pluralsight", "fast.ai"}
CAMPUSES = {"MIT OCW", "Stanford", "Harvard", "UC Berkeley", "Carnegie Mellon", "Caltech"}
CODE = re.compile(r"\b(?:\d{1,2}\.\d{2,4}[a-z]?|(?:cs|cse|ee|ece|cos|math|stat|phys)\s?-?\d{2,4}[a-z]?x?|1[0-9]-\d{3})\b", re.I)
PART = re.compile(r"(?:\bpart\s*|\s)(i{1,3}|iv|[1-4])\b(?!\.\d)", re.I)
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4}


def codes(name):
    return {re.sub(r"[\s-]|x$", "", m.lower()) for m in CODE.findall(name)}


def parts(name):
    stripped = CODE.sub(" ", re.sub(r"\(.*?\)", " ", name))
    return {int(p) if p.isdigit() else ROMAN[p.lower()] for p in PART.findall(stripped)}


def compatible(a, b):
    """False when two catalog entries can't be the same course, whatever the model says.

    a and b may carry "codes": course codes seen in any of their name variants, since the
    display name alone can omit the code that tells two courses apart (6.001 vs 6.0001).
    """
    ca = codes(a["name"]) | a.get("codes", set())
    cb = codes(b["name"]) | b.get("codes", set())
    if ca and cb and not ca & cb:
        return False
    pa, pb = parts(a["name"]), parts(b["name"])
    if pa and pb and pa != pb:
        return False
    spec = re.compile(r"specialization|nanodegree|professional certificate", re.I)
    if bool(spec.search(a["name"])) != bool(spec.search(b["name"])):
        return False
    fa, fb = family(a["provider"]), family(b["provider"])
    mooc_vs_campus = (fa in MOOC_PLATFORMS and fb in CAMPUSES) or (fb in MOOC_PLATFORMS and fa in CAMPUSES)
    if mooc_vs_campus and not ca & cb:
        return False
    return True


SYSTEM = """You maintain a catalog of courses recommended on online forums. You get the current
catalog (id | name | provider) and a batch of newly seen course references (each with its mention
count and spelling variants). For each reference decide whether it is the same course as an existing
catalog entry, or a new course.

Same course: the same course content, even if spelled differently, on a different host (YouTube vs
MIT OCW), a different year/run, or named by instructor ("Andrew Ng's ML course" = "Machine Learning
(Andrew Ng)" on Coursera; "SICP lectures" = "6.001 Structure and Interpretation of Computer Programs").
Different courses: Part I vs Part II; a whole specialization vs one of its courses; a university's
on-campus course vs a MOOC with different material (Stanford CS229 is not Coursera Machine Learning);
same title by different instructors or institutions.

For a new course give a clean canonical name a learner would search for (official title, with a
course code when it is commonly used, e.g. "6.006 Introduction to Algorithms"; add the instructor in
parentheses only when the course is mostly known that way) and a canonical provider (the institution
or platform, e.g. "Coursera", "MIT OpenCourseWare", "Stanford", "fast.ai", "YouTube").
If a reference is not really a course (a book, a tool, a whole platform, a degree), set not_a_course."""

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["ref", "match_id", "not_a_course", "name", "provider"],
        "properties": {
            "ref": {"type": "integer"},
            "match_id": {"type": ["integer", "null"], "description": "catalog id if same course, else null"},
            "not_a_course": {"type": "boolean"},
            "name": {"type": "string", "description": "canonical name if new course, else empty"},
            "provider": {"type": "string", "description": "canonical provider if new course, else empty"},
        },
    }}},
}


def premerge(comments):
    """Group raw (name, provider) pairs whose normalized title and provider family agree."""
    groups = defaultdict(Counter)
    for it in comments:
        for c in it.get("courses", []):
            groups[(family(c["provider"]), norm(c["name"]))][(c["name"], c["provider"])] += 1
    out = []
    for (fam, _), variants in groups.items():
        (name, provider), _ = variants.most_common(1)[0]
        out.append({"name": name, "provider": provider, "family": fam,
                    "count": sum(variants.values()), "variants": [alias_key({"name": n, "provider": p}) for n, p in variants]})
    out.sort(key=lambda g: -g["count"])
    return out


DEDUPE_SYSTEM = """You get a catalog of courses (id | name | provider) built incrementally, so some
courses appear more than once under slightly different names or providers. Return groups of ids that
are the same course (same content; different host, run or spelling is still the same course). Part I
vs Part II, a specialization vs one of its courses, and different instructors are different courses.
Only list groups with 2+ ids; put the id with the best canonical name first."""

DEDUPE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["groups"],
    "properties": {"groups": {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}}},
}


def resolve(cat, cid):
    """Follow merged_into to the surviving entry."""
    seen = set()
    while "merged_into" in cat["courses"][cid] and cid not in seen:
        seen.add(cid)
        cid = cat["courses"][cid]["merged_into"]
    return cid


def merge_into(cat, keep, dup):
    """Record a merge as a link; aliases keep pointing at their original entry so it can be undone."""
    keep, dup = resolve(cat, keep), resolve(cat, dup)
    if keep == dup:  # the model can list an id twice, or both already share a root
        return
    cat["courses"][dup]["merged_into"] = keep


def entry_codes(cat):
    """Surviving catalog id -> course codes found in any alias that resolves to it."""
    out = defaultdict(set)
    for a, target in cat["aliases"].items():
        if target is not None:
            out[resolve(cat, target)] |= codes(a.split("|")[0])
    return out


def with_codes(course, code_map):
    return {**course, "codes": code_map.get(course["id"], set())}


def dedupe(cat, key):
    """Collapse catalog entries created separately for the same course."""
    live = [c for c in cat["courses"] if "merged_into" not in c]
    seen = {}
    for c in live:  # exact duplicates first
        k = (family(c["provider"]), norm(c["name"]))
        if k in seen:
            merge_into(cat, seen[k], c["id"])
        else:
            seen[k] = c["id"]
    live = [c for c in cat["courses"] if "merged_into" not in c]
    listing = "\n".join(f"{c['id']} | {c['name']} | {c['provider']}" for c in sorted(live, key=lambda c: norm(c["name"])))
    result, cost = structured(key, DEDUPE_MODEL, DEDUPE_SYSTEM, f"<catalog>\n{listing}\n</catalog>",
                              DEDUPE_SCHEMA, max_tokens=16000, effort="medium")
    ids = {c["id"] for c in live}
    merged = 0
    for group in result["groups"]:
        group = [i for i in group if i in ids]
        for dup in group[1:]:
            code_map = entry_codes(cat)  # codes accumulate as entries merge
            keep_c, dup_c = cat["courses"][resolve(cat, group[0])], cat["courses"][resolve(cat, dup)]
            if keep_c["id"] != dup_c["id"] and compatible(with_codes(keep_c, code_map), with_codes(dup_c, code_map)):
                merge_into(cat, keep_c["id"], dup_c["id"])
                merged += 1
    print(f"dedupe: merged {merged} entries, ${cost:.3f}", flush=True)


def origin(course):
    return course.get("origin", "hn")


def dedupe_reddit(cat, key):
    """Like dedupe, but only for Reddit-created entries: existing merges are kept, a Reddit entry
    joins the HN entry of its group when there is one, and a cluster holding an hn entry is never
    merged into anything (so two hn entries are never joined)."""
    live = [c for c in cat["courses"] if "merged_into" not in c]
    listing = "\n".join(f"{c['id']} | {c['name']} | {c['provider']}" for c in sorted(live, key=lambda c: norm(c["name"])))
    result, cost = structured(key, DEDUPE_MODEL, DEDUPE_SYSTEM, f"<catalog>\n{listing}\n</catalog>",
                              DEDUPE_SCHEMA, max_tokens=16000, effort="medium")
    ids = {c["id"] for c in live}

    def has_hn(root):
        return any(origin(c) == "hn" for c in cat["courses"] if resolve(cat, c["id"]) == root)

    merged = 0
    for group in result["groups"]:
        group = [i for i in group if i in ids]
        if len(group) < 2:
            continue
        # Keep the HN cluster when there is one, whatever order the model listed the ids in.
        keeper = next((i for i in group if has_hn(resolve(cat, i))), group[0])
        for other in group:
            code_map = entry_codes(cat)
            keep_c, dup_c = cat["courses"][resolve(cat, keeper)], cat["courses"][resolve(cat, other)]
            # Only Reddit-only clusters move; an HN-containing cluster is never merged into anything.
            if keep_c["id"] == dup_c["id"] or origin(dup_c) != "reddit" or has_hn(dup_c["id"]):
                continue
            if compatible(with_codes(keep_c, code_map), with_codes(dup_c, code_map)):
                merge_into(cat, keep_c["id"], dup_c["id"])
                merged += 1
    print(f"dedupe-reddit: merged {merged} entries, ${cost:.3f}", flush=True)


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def save_catalog(cat):
    CATALOG.write_text(json.dumps(cat, ensure_ascii=False, indent=0), encoding="utf-8")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Map course names to canonical catalog entries.")
    ap.add_argument("--source", choices=SOURCES, default="hn")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dedupe", action="store_true",
                      help="HN-wide: clear every merge and dedupe the whole catalog again")
    mode.add_argument("--dedupe-reddit", action="store_true",
                      help="dedupe Reddit-created entries only; HN entries and merges are kept")
    ap.add_argument("limit", nargs="?", type=int, help="map at most this many pre-merged names")
    args = ap.parse_args(argv)
    if args.dedupe and args.source != "hn":
        ap.error("--dedupe is HN-wide; use --dedupe-reddit for Reddit entries")
    return args


def main():
    args = parse_args()
    key = api_key()
    if args.dedupe_reddit:
        cat = load_catalog()
        dedupe_reddit(cat, key)
        save_catalog(cat)
        return
    if args.dedupe:
        cat = load_catalog()
        if any(origin(c) == "reddit" for c in cat["courses"]):
            raise SystemExit("--dedupe clears every merge, including Reddit ones; the catalog has Reddit "
                             "entries, so use --dedupe-reddit instead")
        for c in cat["courses"]:  # merges are links only, so a re-run starts clean
            c.pop("merged_into", None)
        dedupe(cat, key)
        save_catalog(cat)
        return
    source = args.source
    comments = json.loads(paths(source).courses.read_text(encoding="utf-8"))
    groups = premerge(comments)
    cat = load_catalog() if CATALOG.exists() else {"courses": [], "aliases": {}}
    todo = [g for g in groups if not all(v in cat["aliases"] for v in g["variants"])]
    limit = args.limit if args.limit is not None else len(todo)
    todo = todo[:limit]
    print(f"{len(groups)} pre-merged names, {len(todo)} to map, catalog has {len(cat['courses'])}", flush=True)

    cost = 0.0
    for start in range(0, len(todo), BATCH):
        batch = todo[start:start + BATCH]
        catalog_txt = "\n".join(f"{c['id']} | {c['name']} | {c['provider']}"
                                for c in cat["courses"] if "merged_into" not in c) or "(empty)"
        refs = "\n".join(
            f"{i} | {g['name']} | {g['provider']} | mentions={g['count']}"
            + (f" | variants: {'; '.join(v.split('|')[0] for v in g['variants'][1:4])}" if len(g["variants"]) > 1 else "")
            for i, g in enumerate(batch))
        user = f"<catalog>\n{catalog_txt}\n</catalog>\n\n<references>\n{refs}\n</references>"
        result, c = structured(key, MODEL, SYSTEM, user, SCHEMA, max_tokens=16000)
        cost += c
        valid_ids = {x["id"] for x in cat["courses"] if "merged_into" not in x}
        code_map = entry_codes(cat)
        for r in result["items"]:
            if not 0 <= r["ref"] < len(batch):
                continue
            g = batch[r["ref"]]
            g_codes = {code for v in g["variants"] for code in codes(v.split("|")[0])}
            if r["not_a_course"]:
                target = None
            elif r["match_id"] in valid_ids and compatible(
                    {**g, "codes": g_codes}, with_codes(cat["courses"][r["match_id"]], code_map)):
                target = r["match_id"]
            else:
                target = len(cat["courses"])
                cat["courses"].append({"id": target, "name": r["name"] or g["name"], "provider": r["provider"] or g["provider"],
                                   "origin": source})
                valid_ids.add(target)
            for v in g["variants"]:
                if source == "hn":
                    cat["aliases"][v] = target
                else:  # a Reddit run only adds aliases; ones HN already mapped are never rewritten
                    cat["aliases"].setdefault(v, target)
        save_catalog(cat)
        print(f"{min(start + BATCH, len(todo))}/{len(todo)}  catalog={len(cat['courses'])}  ${cost:.3f}", flush=True)


if __name__ == "__main__":
    main()
