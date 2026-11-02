import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pages  # noqa: E402

T = 1_710_000_000


def course(i, name, topic="Programming"):
    return {"id": i, "slug": name.lower(), "name": name, "provider": "Prov", "topic": topic, "summary": "s", "why": "w",
            "level": "unknown", "cost": "free", "img": None, "imgTall": False, "rank": i, "badges": [],
            "recommenders": 3, "threads": 2, "first": T, "last": T, "score": 1.0}


def render(source, extra=None):
    meta = {"courses": 2, "comments": 1234, "data_end": T, "reddit": True,
            "topics": {"hn": {"programming"}, "reddit": {"programming"}}} | (extra or {})
    cs = [course(1, "Alpha"), course(2, "Beta")]
    pages.TOPIC_PAGES[source][:] = [("Programming", "programming", 2)]
    return pages.index_page(meta, cs, source), pages.topic_page("Programming", "programming", cs, meta, source)


def test_switch_marks_active_source():
    html = pages.source_switch("reddit")
    assert '<a href="/" data-source="hn">Hacker News</a>' in html
    assert '<a href="/reddit/" data-source="reddit" aria-current="page">Reddit</a>' in html
    assert html.count("aria-current") == 1
    assert 'aria-label="Source"' in html and 'class="source-switch"' in html
    assert 'data-source="hn" aria-current="page"' in pages.source_switch("hn")


def test_reddit_home_copy_and_search_action():
    home, topic = render("reddit")
    assert "<title>Hacker Courses: the online courses Reddit recommends</title>" in home
    assert "<h1 class=\"visually-hidden\">The online courses recommended most on Reddit</h1>" in home
    assert 'action="/reddit/"' in home
    assert "ranked from 1,234 public comments in 30 communities." in home
    assert "/reddit/courses.js" in home
    assert "Best Programming courses, as recommended on Reddit" in topic
    assert 'href="/topic/programming/"' in topic  # switch points at the HN twin of this topic
    assert 'action="/reddit/"' in topic


def test_hn_home_title_unchanged():
    home, topic = render("hn")
    assert "<title>Hacker Courses: the online courses programmers recommend on Hacker News</title>" in home
    assert 'action="/"' in home
    assert '<a href="/reddit/topic/programming/" data-source="reddit">Reddit</a>' in topic
    assert "/courses.js" in home and "/reddit/courses.js" not in home


def test_topic_switch_falls_back_to_home_when_other_source_lacks_topic():
    _, topic = render("hn", {"topics": {"hn": {"programming"}, "reddit": set()}})
    assert '<a href="/reddit/" data-source="reddit">Reddit</a>' in topic


def test_no_reddit_courses_means_no_switch_or_reddit_links():
    home, topic = render("hn", {"reddit": False})
    for html in (home, topic):
        assert "source-switch" not in html and "/reddit/" not in html
