import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import pages  # noqa: E402
import sources  # noqa: E402

T = 1_710_000_000


@pytest.fixture(autouse=True)
def isolated_module_state(monkeypatch):
    """pages keeps per-run state in module globals; give every test its own copy."""
    monkeypatch.setattr(pages, "TOPIC_PAGES", {"hn": [], "reddit": []})
    monkeypatch.setattr(pages, "SPAN", pages.SPAN)
    monkeypatch.setattr(pages, "TAGLINE", pages.TAGLINE)
    monkeypatch.setattr(pages, "REDDIT_COMMUNITIES", 30)
    monkeypatch.setattr(pages, "REDDIT_SUBS", list(sources.SUBREDDITS))


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


# ---- course pages, About, credits, llms files ------------------------------------

HN_CM = {"id": 11, "by": "alice", "t": T, "text": "Great course", "thread": "Ask HN: learn CS?", "tid": 5}
RD_CM = {"id": "abc", "by": "bob", "t": T, "text": "z" * 299 + "…", "thread": "Where to learn?", "tid": "t3_x",
         "src": "reddit", "sub": "learnprogramming", "ups": 42, "age": 90 * 86400,
         "url": "https://www.reddit.com/r/learnprogramming/comments/x/_/abc/"}
COMMENTS = [HN_CM, RD_CM]


def stats(rank, ends, **kw):
    return {"rank": rank, "badges": [], "recommenders": 3, "threads": 2, "first": T, "last": T, "years_active": 1,
            "score": 1.5, "trend": 1.0, "endorsements": ends} | kw


def merged(i, name, **srcs):
    return {"id": i, "slug": name.lower(), "name": name, "provider": "Prov", "topic": "General Learning",
            "summary": "A summary", "why": "Because", "level": "unknown", "cost": "free", "format": "unknown",
            "tags": [], "img": None, "imgPage": None, "imgTall": False, "url": "https://example.com/" + name,
            "related": [], "sources": srcs}


def page(c, by_id=None, **kw):
    return pages.course_page(c, COMMENTS, by_id or {c["id"]: c}, T, **kw)


def test_course_page_two_sources():
    c = merged(1, "Both", hn=stats(12, [[0, 3]], recommenders=5),
               reddit=stats(340, [[1, 2]], recommenders=4, badges=["rising"]))
    html = page(c, multi=True)
    assert '<h2 class="section-h">On Hacker News (1)</h2>' in html
    assert '<h2 class="section-h">On Reddit (1)</h2>' in html
    assert "#12 on Hacker News" in html and "#340 on Reddit" in html
    assert 'href="https://www.reddit.com/r/learnprogramming/comments/x/_/abc/"' in html
    assert "Open on Reddit ↗" in html and "r/learnprogramming" in html and "▲ 42" in html
    assert "Where to learn?" in html and "bob" in html
    assert "z" * 299 in html and "z" * 300 not in html
    assert "Read all" not in html  # Reddit excerpts are never expanded
    assert "· recommended on Hacker News and Reddit</title>" in html
    assert "recommended by 5 Hacker News commenters and 4 Redditors, 2024." in html
    assert html.count('class="bars"') == 2
    assert 'class="badge rising"' in html


def test_course_page_single_source():
    rd = page(merged(2, "Solo", reddit=stats(7, [[1, 3]], recommenders=2)))
    assert "On Hacker News" not in rd and '<h2 class="section-h">On Reddit (1)</h2>' in rd
    assert "· Reddit recommendations</title>" in rd
    assert "recommended by 2 Redditors, 2024." in rd
    assert "#7 on Reddit" in rd
    assert 'href="/reddit/"' in rd and 'href="/reddit/topic/general-learning/"' in rd
    hn = page(merged(1, "Plain", hn=stats(3, [[0, 3]])))
    assert "· Hacker News recommendations</title>" in hn
    assert "#3 overall" in hn and "What commenters said (1)" in hn and "On Reddit" not in hn
    assert "recommended by 3 Hacker News commenters, 2024." in hn


def test_hn_course_on_a_reddit_site_names_its_ranking():
    html = page(merged(1, "Plain", hn=stats(3, [[0, 3]])), multi=True)
    assert "#3 on Hacker News" in html and "overall" not in html
    assert "· Hacker News recommendations</title>" in html


def test_prev_next_baked_from_the_courses_own_ranking():
    c = merged(2, "Solo", reddit=stats(7, [[1, 3]]))
    c["prev"], c["next"] = {"slug": "p", "name": "Pee"}, None
    html = page(c)
    assert 'id="prevLink" href="/course/p/"' in html and "nextLink" not in html


def test_timeline_has_a_labelled_row_per_source():
    both = merged(1, "Both", hn=stats(1, [[0, 3]]), reddit=stats(1, [[1, 3]]))
    tl = pages.timeline(both, COMMENTS, T)
    assert tl.count('class="bars"') == 2 and "Hacker News" in tl and "Reddit" in tl
    only_hn = pages.timeline(merged(1, "H", hn=stats(1, [[0, 3]])), COMMENTS, T)
    assert only_hn.count('class="bars"') == 1 and "bars-label" not in only_hn
    rd = pages.timeline(merged(2, "R", reddit=stats(1, [[1, 3]])), COMMENTS, T)
    assert rd.count('class="bars"') == 1 and "<span>2024</span>" in rd


def test_footer_credits_each_source_used(monkeypatch):
    plain = pages.footer("hn")
    assert "Not affiliated with Y Combinator or Hacker News." in plain and "Reddit" not in plain
    monkeypatch.setitem(pages.TOPIC_PAGES, "reddit", [("General Learning", "general-learning", 1)])
    for src in ("hn", "reddit"):
        f = pages.footer(src)
        assert "https://academictorrents.com/details/56aa49f9653ba545f48df2e33679f014d2829c10" in f
        assert "Watchful1" in f and "https://www.redditinc.com/policies/user-agreement" in f
        assert "nixiesearch/hackernews-comments" in f
        assert "Not affiliated with Y Combinator, Hacker News or Reddit." in f


REDDIT_META = {"courses": 2, "comments": 100, "data_end": T, "reddit": True, "reddit_comments": 40,
               "reddit_subs": ["Entrepreneur", "startups", "learnprogramming", "ChatGPT"],
               "reddit_years": (2021, 2023)}


def test_about_reddit_section_only_when_reddit_present():
    plain = pages.about_page({"courses": 2, "comments": 100, "data_end": T})
    assert "Reddit" not in plain and "isBasedOn" not in plain
    html = pages.about_page(REDDIT_META)
    assert ">Reddit</h2>" in html
    assert "r/learnprogramming" in html and "r/ClaudeAI" not in html and "r/PKMS" not in html
    assert "Business &amp; entrepreneurship" in html and "AI &amp; ML" in html
    assert "Marketing &amp; growth" not in html  # no present subreddit in that group
    assert "up to twice" in html and "30 days" in html and "excerpts" in html
    ld = re.search(r'application/ld\+json">(.*?)</script>', html).group(1)
    assert "isBasedOn" in ld and "academictorrents.com" in ld and "nixiesearch/hackernews-comments" in ld
    assert "no license or terms were published" in html.lower()


def test_subreddit_groups_cover_the_configured_list():
    grouped = [s for _, subs in pages.SUBREDDIT_GROUPS for s in subs]
    assert sorted(grouped) == sorted(sources.SUBREDDITS)


def test_llms_files_with_reddit():
    hn = merged(1, "Both", hn=stats(1, [[0, 3]]), reddit=stats(5, [[1, 3]]))
    rd = merged(2, "Solo", reddit=stats(1, [[1, 3]]))
    hv = [pages.view(hn, "hn")]
    rv = [pages.view(rd, "reddit"), pages.view(hn, "reddit")]
    txt = pages.llms_txt(hv, REDDIT_META, {"General Learning": hv}, rv)
    assert "## Top 30 on Reddit" in txt and "/course/solo/" in txt
    assert "Not affiliated with Y Combinator, Hacker News or Reddit." in txt
    assert "academictorrents.com/details/56aa49f9653ba545f48df2e33679f014d2829c10" in txt
    full = pages.llms_full_txt([hn, rd], REDDIT_META)
    assert "#1 on Hacker News" in full and "#5 on Reddit" in full and "#1 on Reddit" in full
    assert full.index("Both") < full.index("Solo")
    assert "academictorrents.com/details/56aa49f9653ba545f48df2e33679f014d2829c10" in full
    assert "3 online courses" in pages.llms_full_txt([hn, rd], REDDIT_META | {"total": 3})
    plain_meta = {"courses": 1, "comments": 5, "data_end": T}
    assert "Reddit" not in pages.llms_txt(hv, plain_meta, {"General Learning": hv})
    assert "Reddit" not in pages.llms_full_txt([hn], plain_meta)


def test_write_all_with_both_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(pages, "SITE", tmp_path)
    (tmp_path / "course").mkdir()
    both = merged(1, "Both", hn=stats(1, [[0, 3]]), reddit=stats(2, [[1, 3]]))
    only_rd = merged(2, "Solo", reddit=stats(1, [[1, 3]]))
    only_rd["related"] = [1]
    both["related"] = [2]
    pages.write_all([both, only_rd], COMMENTS, T)
    assert (tmp_path / "index.html").exists() and (tmp_path / "reddit" / "index.html").exists()
    assert (tmp_path / "reddit" / "topic" / "general-learning" / "index.html").exists()
    solo = (tmp_path / "course" / "solo" / "index.html").read_text(encoding="utf-8")
    assert "· Reddit recommendations</title>" in solo
    assert "/course/solo/" in (tmp_path / "course" / "both" / "index.html").read_text(encoding="utf-8")  # related
    sm = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    for u in ("/reddit/", "/reddit/topic/general-learning/", "/course/solo/", "/course/both/", "/topic/general-learning/"):
        assert f"<loc>{pages.BASE}{u}</loc>" in sm
    assert "Top 30 on Reddit" in (tmp_path / "llms.txt").read_text(encoding="utf-8")
    assert "Solo" in (tmp_path / "llms-full.txt").read_text(encoding="utf-8")


def test_write_all_removes_stale_reddit_pages_when_data_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(pages, "SITE", tmp_path)
    stale = tmp_path / "reddit" / "topic" / "old"
    stale.mkdir(parents=True)
    (stale / "index.html").write_text("x")
    (tmp_path / "reddit" / "index.html").write_text("x")
    pages.write_all([merged(1, "Plain", hn=stats(1, [[0, 3]]))], COMMENTS, T)
    assert not list((tmp_path / "reddit").rglob("*.html"))
    assert "reddit" not in (tmp_path / "sitemap.xml").read_text(encoding="utf-8").lower()
    assert "Reddit" not in (tmp_path / "about" / "index.html").read_text(encoding="utf-8")


def test_upvotes_hidden_when_captured_too_soon_or_age_unknown():
    shown = pages.comment_item(RD_CM, 3, "reddit")
    assert "▲ 42" in shown
    for age in (None, 29 * 86400):
        assert "▲" not in pages.comment_item(RD_CM | {"age": age}, 3, "reddit")
    assert "▲" not in pages.comment_item({k: v for k, v in RD_CM.items() if k != "age"}, 3, "reddit")


def test_reddit_home_and_sitemap_use_the_reddit_data_end(tmp_path, monkeypatch):
    monkeypatch.setattr(pages, "SITE", tmp_path)
    (tmp_path / "course").mkdir()
    rd_end = T - 400 * 86400
    both = merged(1, "Both", hn=stats(1, [[0, 3]]), reddit=stats(2, [[1, 3]]))
    pages.write_all([both], COMMENTS, T, rd_end)
    sm = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert f"<loc>{pages.BASE}/reddit/</loc><lastmod>{pages.iso(rd_end)}</lastmod>" in sm
    assert f"<loc>{pages.BASE}/</loc><lastmod>{pages.iso(T)}</lastmod>" in sm
    assert f'"dateModified": "{pages.iso(rd_end)}"' in (tmp_path / "reddit" / "index.html").read_text(encoding="utf-8")
    assert f'"dateModified": "{pages.iso(T)}"' in (tmp_path / "index.html").read_text(encoding="utf-8")
