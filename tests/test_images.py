import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from images import drop_shared  # noqa: E402


def img(src):
    return {"src": src, "page": src, "w": 640, "h": 360}


def test_reddit_entries_do_not_drop_hn_art():
    done = {"1": img("a"), "2": img("a"), "3": img("a")}
    drop_shared(done, {"1": "hn", "2": "hn", "3": "reddit"})
    assert done["1"] and done["2"] and done["3"]


def test_three_courses_in_one_source_share_a_default():
    done = {"1": img("a"), "2": img("a"), "3": img("a"), "4": img("b")}
    assert drop_shared(done, {"3": "reddit"} | {k: "hn" for k in "124"}) == 0
    done = {"1": img("a"), "2": img("a"), "5": img("a"), "4": img("b")}
    assert drop_shared(done, {}) == 1
    assert done["1"] is None and done["5"] is None and done["4"]
