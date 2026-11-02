"""Course ranking.

Comment karma is not public, so the score rests on who recommended a course, how strongly,
in how many separate discussions, and for how long:

1. Stance weight per comment: strongly recommends 1.0, recommends 0.7, mentions 0.25,
   criticizes 0 (criticism is shown, it just earns no points).
2. One vote per person: an author who recommends a course five times counts once, at their
   strongest stance.
3. Pile-on damping: within one thread, votes are sorted and decay geometrically
   (1, 1/2, 1/4, ...), so ten replies in one "Ask HN" thread are worth at most two independent
   ones, while the same course surfacing in ten unrelated threads counts ten times.
4. Staying power: x(1 + 0.08 per extra calendar year with a recommendation), so a course people
   still recommend a decade later outranks a one-season fad with the same votes.

score = sum over threads of damped votes  x  staying-power multiplier

"Trending" uses the same votes with a 2-year half-life back from the newest comment in the data.
"""

import time
from collections import defaultdict

STANCE_WEIGHT = {"strongly_recommends": 1.0, "recommends": 0.7, "mentions": 0.25, "criticizes": 0.0}
THREAD_DECAY = 0.5
YEAR_BONUS = 0.08
HALF_LIFE_YEARS = 2.0
YEAR = 365.25 * 24 * 3600


def author_votes(endorsements):
    """endorsements: [{author, thread, time, stance}] -> one strongest vote per author."""
    best = {}
    for e in endorsements:
        w = STANCE_WEIGHT[e["stance"]]
        if e["author"] not in best or w > best[e["author"]]["w"]:
            best[e["author"]] = {**e, "w": w}
    return list(best.values())


def damped(votes, weight=lambda v: v["w"]):
    by_thread = defaultdict(list)
    for v in votes:
        by_thread[v["thread"]].append(weight(v))
    total = 0.0
    for ws in by_thread.values():
        total += sum(w * THREAD_DECAY ** i for i, w in enumerate(sorted(ws, reverse=True)))
    return total


def score(endorsements):
    votes = author_votes(endorsements)
    years = {time.gmtime(e["time"]).tm_year for e in endorsements if STANCE_WEIGHT[e["stance"]] > 0}
    return damped(votes) * (1 + YEAR_BONUS * max(0, len(years) - 1))


def trending(endorsements, now):
    votes = author_votes(endorsements)
    return damped(votes, lambda v: v["w"] * 0.5 ** ((now - v["time"]) / (HALF_LIFE_YEARS * YEAR)))


def badges(course, rank, n_courses, now):
    """course: dict with recommenders, years_active, first, last, strong_share, recent_share."""
    out = []
    span = time.gmtime(course["last"]).tm_year - time.gmtime(course["first"]).tm_year
    if rank < max(25, n_courses // 50) and span >= 8:
        out.append("classic")
    if course["years_active"] >= 6 and span >= 8:
        out.append("evergreen")
    if course["recommenders"] >= 3 and course["recent_share"] >= 0.6:
        out.append("rising")
    if 2 <= course["recommenders"] <= 4 and course["strong_share"] >= 0.75:
        out.append("hidden gem")
    return out


def recent_share(endorsements, now, years=3):
    votes = author_votes(endorsements)
    total = sum(v["w"] for v in votes) or 1.0
    return sum(v["w"] for v in votes if now - v["time"] <= years * YEAR) / total
