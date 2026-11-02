import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import classify  # noqa: E402
import reddit  # noqa: E402

RECOMMEND = "I'd recommend HubSpot Academy's inbound marketing course, it's free"


def hn(text):
    return {"id": "1", "by": "u", "time": 1_700_000_000, "text": text}


def rd(text):
    return {"id": "t1_abc", "by": "u", "time": 1_700_000_000, "text": text, "src": "reddit",
            "sub": "marketing", "ups": 12, "age": 40 * 86400, "thread": "t3_xyz"}


def test_reddit_vendor_course_kept():
    item, why = classify.classify(rd(RECOMMEND), "reddit")
    assert why == "kept"
    assert item["topic"] == "Marketing & Growth"
    assert (item["src"], item["sub"], item["ups"], item["age"], item["thread"]) == (
        "reddit", "marketing", 12, 40 * 86400, "t3_xyz")


def test_same_text_on_hn_unchanged():
    # Snapshot of the pre-Reddit verdict, except the topic: marketing now has its own bucket.
    item, why = classify.classify(hn(RECOMMEND))
    assert why == "kept"
    assert item == {"id": "1", "by": "u", "time": 1_700_000_000, "text": RECOMMEND, "links": [],
                    "topic": "Marketing & Growth", "score": 3}
    assert "src" not in item


def test_reddit_only_course_rejected_on_hn():
    text = "HubSpot Academy has a great free course on this topic, worth it"
    assert classify.classify(hn(text)) == (None, "no-recommendation")
    assert classify.classify(rd(text), "reddit")[1] == "kept"


def test_reddit_spam():
    text = "Great course, link in my bio. I'd recommend the Skillshare course on this"
    assert classify.classify(rd(text), "reddit") == (None, "spam")


def test_reddit_spam_pattern_not_applied_to_hn():
    text = "Highly recommend the Coursera course on algorithms, pm me if you want tips"
    assert classify.classify(hn(text))[1] == "kept"
    assert classify.classify(rd(text), "reddit") == (None, "spam")


def test_reddit_markdown_link_counts_as_course_link():
    item, why = classify.classify(rd("[Maven course](https://maven.com/x) is worth it, highly recommend"), "reddit")
    assert why == "kept"
    assert item["links"] == ["https://maven.com/x"]


def test_maven_build_tool_is_not_a_named_course():
    text = "You should recommend this course to anyone: mvn / maven build failed for me on the java class"
    assert classify.classify(rd(text), "reddit")[1] != "kept"
    assert not reddit.PREFILTER.search("mvn / maven build failed")
    assert reddit.PREFILTER.search("the Maven course on pricing")


def test_new_topics_take_marketing_and_productivity_from_business():
    assert classify.topic_of("a seo and copywriting course", []) == "Marketing & Growth"
    assert classify.topic_of("a course on habits and deep work", []) == "Productivity & Personal Development"
    assert classify.topic_of("a course on venture finance", []) == "Business, Finance & Economics"


def test_reddit_rows_from_dropped_subreddits_are_discarded():
    import json
    row = rd(RECOMMEND)
    assert classify.classify_line(json.dumps(row), "reddit")[1] == "kept"
    assert classify.classify_line(json.dumps(row | {"sub": "Marketing"}), "reddit")[1] == "kept"
    assert classify.classify_line(json.dumps(row | {"sub": "bigseo"}), "reddit") == (None, "dropped-subreddit")
    assert classify.classify_line(json.dumps(row | {"sub": "bigseo"}))[1] != "dropped-subreddit"
