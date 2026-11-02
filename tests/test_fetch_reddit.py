import io
import json
import sys
from pathlib import Path

import zstandard

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import fetch_reddit  # noqa: E402
import sources  # noqa: E402

T = 1_700_000_000  # 2023-11-14


def write_zst(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = ("\n".join(lines) + "\n").encode()
    path.write_bytes(zstandard.ZstdCompressor().compress(data))


def comment(cid, body, created=T, link="t3_xyz", sub="learnprogramming"):
    return json.dumps({"id": cid, "author": "u1", "body": body, "created_utc": created, "subreddit": sub,
                       "score": 5, "link_id": link, "retrieved_on": created + 90 * 86400})


def test_read_dump_streams_and_skips_bad_lines(tmp_path):
    p = tmp_path / "x_comments.zst"
    write_zst(p, ['{"id": "a"}', "{not json", '{"id": "b"}'])
    assert [d["id"] for d in fetch_reddit.read_dump(p)] == ["a", "b"]


def run(tmp_path, monkeypatch, *args):
    raw = tmp_path / "raw"
    write_zst(raw / "learnprogramming_submissions.zst", [
        json.dumps({"id": "xyz", "title": "Best SEO course?", "subreddit": "learnprogramming", "created_utc": T})])
    write_zst(raw / "learnprogramming_comments.zst", [
        comment("a", "Highly recommend the Coursera course"),
        comment("b", "[removed]"),
        comment("old", "Take this course too", created=T - 400 * 86400),
    ])
    fake = sources.Paths(*(tmp_path / n for n in ("c.jsonl", "p.json", "l.jsonl", "co.json", "t.json", "s.jsonl")))
    monkeypatch.setattr(fetch_reddit, "paths", lambda s: fake)
    monkeypatch.setattr(sys, "argv", ["fetch_reddit.py", "--raw", str(raw), *args])
    fetch_reddit.main()
    return fake


def test_main_writes_candidates_and_threads(tmp_path, monkeypatch, capsys):
    fake = run(tmp_path, monkeypatch)
    rows = [json.loads(line) for line in fake.candidates.read_text(encoding="utf-8").splitlines()]
    assert sorted(r["id"] for r in rows) == ["t1_a", "t1_old"]  # no --since: nothing excluded, [removed] dropped
    threads = json.loads(fake.threads.read_text(encoding="utf-8"))
    assert threads["t1_a"] == ["t3_xyz", "Best SEO course?"]
    assert "learnprogramming" in capsys.readouterr().out


def test_threads_only_for_kept_comments_and_since_filters(tmp_path, monkeypatch):
    fake = run(tmp_path, monkeypatch, "--since", "2023-01-01")
    rows = [json.loads(line) for line in fake.candidates.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1 and rows[0]["id"] == "t1_a"
    assert json.loads(fake.threads.read_text(encoding="utf-8")) == {"t1_a": ["t3_xyz", "Best SEO course?"]}


def test_until_excludes_newer_and_rerun_does_not_duplicate(tmp_path, monkeypatch):
    fake = run(tmp_path, monkeypatch, "--since", "2023-01-01", "--until", "2023-11-01")
    assert fake.candidates.read_text(encoding="utf-8") == ""
    fake = run(tmp_path, monkeypatch, "--since", "2023-01-01")
    fake = run(tmp_path, monkeypatch, "--since", "2023-01-01")
    assert len(fake.candidates.read_text(encoding="utf-8").splitlines()) == 1
