import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import sources  # noqa: E402
import summarize  # noqa: E402

CAT = {"courses": [{"id": 0, "name": "CS50", "provider": "Harvard"}],
       "aliases": {"CS50|Harvard": 0}}


def setup(tmp_path, monkeypatch):
    def fake_paths(source):
        d = tmp_path if source == "hn" else tmp_path / "reddit"
        d.mkdir(exist_ok=True)
        return sources.Paths(d / "candidates.jsonl", d / "pool.json", d / "llm_labels.jsonl",
                             d / "courses.json", d / "threads.json", d / "summaries.jsonl")
    monkeypatch.setattr(sources, "paths", fake_paths)
    cat = tmp_path / "catalog.json"
    cat.write_text(json.dumps(CAT), encoding="utf-8")
    monkeypatch.setattr(summarize, "CATALOG", cat)
    hn = [{"id": 42, "text": "CS50 is great", "links": [], "courses": [{"name": "CS50", "provider": "Harvard"}]}]
    rd = [{"id": "t1_abc", "src": "reddit", "sub": "learnprogramming", "text": "CS50 changed my life",
           "links": [], "courses": [{"name": "CS50", "provider": "Harvard"}]}]
    sources.paths("hn").courses.write_text(json.dumps(hn), encoding="utf-8")
    sources.paths("reddit").courses.write_text(json.dumps(rd), encoding="utf-8")
    sources.paths("reddit").threads.write_text(json.dumps({"t1_abc": ["t3_x", "Best CS course?"]}), encoding="utf-8")
    return fake_paths


def test_course_comments_tags_sources_and_keeps_ids_distinct(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    _, both = summarize.course_comments()
    assert {(it["src"], it["id"]) for it in both[0]} == {("hn", 42), ("reddit", "t1_abc")}
    _, hn = summarize.course_comments("hn")
    assert [it["id"] for it in hn[0]] == [42]
    _, rd = summarize.course_comments("reddit")
    assert [it["id"] for it in rd[0]] == ["t1_abc"]


def test_reddit_run_never_writes_hn_summaries(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    hn_file = sources.paths("hn").summaries
    hn_file.write_text(json.dumps({"id": 0, "summary": "s", "stances": {"42": "recommends"},
                                   "comment_ids": [42]}) + "\n", encoding="utf-8")
    before = hn_file.read_bytes()
    prompts = []

    def fake_structured(key, model, system, user, schema, max_tokens=0):
        prompts.append(user)
        return {"summary": "x", "why": "y", "level": "unknown", "cost": "free", "format": "mixed", "tags": [],
                "url_index": None, "topic": "other",
                "stances": [{"comment_id": "t1_abc", "stance": "strongly_recommends"}]}, 0.0

    monkeypatch.setattr(summarize, "structured", fake_structured)
    monkeypatch.setattr(summarize, "api_key", lambda: "k")
    monkeypatch.setattr(sys, "argv", ["summarize.py", "--source", "reddit"])
    summarize.main()
    assert hn_file.read_bytes() == before
    lines = [json.loads(x) for x in sources.paths("reddit").summaries.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["stances"] == {"t1_abc": "strongly_recommends"}
    assert lines[0]["comment_ids"] == ["t1_abc"]
    assert 'thread="Best CS course?"' in prompts[0] and "CS50 is great" not in prompts[0]
    assert summarize.load("reddit")[0]["stances"] == {"t1_abc": "strongly_recommends"}
    assert summarize.load("hn")[0]["comment_ids"] == [42]
