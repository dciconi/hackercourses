import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from canonicalize import compatible, merge_into, resolve  # noqa: E402


def c(name, provider):
    return {"name": name, "provider": provider}


def test_part_numbers_must_agree():
    assert not compatible(c("Cryptography I", "Coursera"), c("Cryptography II", "Coursera"))
    assert not compatible(c("Algorithms, Part I", "Coursera"), c("Algorithms, Part II", "Coursera"))
    assert compatible(c("Cryptography I", "Coursera"), c("Crypto I (Dan Boneh)", "Coursera"))
    assert compatible(c("Cryptography I", "Coursera"), c("Cryptography 1", "Coursera"))


def test_specialization_is_not_one_course():
    assert not compatible(c("Algorithms, Part I", "Coursera"), c("Algorithms Specialization", "Coursera"))


def test_different_course_codes_never_merge():
    assert not compatible(c("CS229 Machine Learning", "Stanford"), c("CS231n Convolutional Networks", "Stanford"))
    assert compatible(c("6.001 Structure and Interpretation of Computer Programs", "MIT OCW"),
                      c("SICP lectures (Abelson and Sussman)", "YouTube"))


def test_codes_come_from_every_variant_not_just_the_display_name():
    sicp = {**c("6.001 Structure and Interpretation of Computer Programs", "MIT OCW"), "codes": {"6.001"}}
    python = {**c("Introduction to Computer Science and Programming in Python", "MIT OCW"), "codes": {"6.00", "6.0001"}}
    assert not compatible(sicp, python)


def test_dedupe_merges_are_links_and_reversible():
    cat = {"courses": [{"id": 0, **c("A", "X")}, {"id": 1, **c("A2", "X")}], "aliases": {"A2|X": 1}}
    merge_into(cat, 0, 1)
    assert resolve(cat, cat["aliases"]["A2|X"]) == 0
    assert cat["aliases"]["A2|X"] == 1  # alias untouched, so the merge can be undone
    merge_into(cat, 1, 1)
    assert "merged_into" not in cat["courses"][0]


def test_mooc_is_not_the_campus_course_unless_codes_match():
    assert not compatible(c("Machine Learning (Andrew Ng)", "Coursera"), c("CS229 Machine Learning", "Stanford University"))
    assert compatible(c("CS50: Introduction to Computer Science", "Harvard University"), c("CS50x", "edX"))


def test_dedupe_reddit_never_merges_two_hn_entries(monkeypatch):
    import canonicalize
    cat = {"courses": [{"id": 0, **c("Algorithms", "Coursera")},
                       {"id": 1, **c("Algorithms Course", "Coursera")},
                       {"id": 2, **c("Algorithms", "Coursera (Princeton)"), "origin": "reddit"},
                       {"id": 3, **c("Old Dup", "X"), "merged_into": 0},
                       {"id": 4, **c("Other", "Y"), "origin": "reddit"}],
           "aliases": {}}
    monkeypatch.setattr(canonicalize, "structured",
                        lambda *a, **k: ({"groups": [[0, 1, 2]]}, 0.0))
    canonicalize.dedupe_reddit(cat, "key")
    assert cat["courses"][2]["merged_into"] == 0
    assert "merged_into" not in cat["courses"][1]
    assert cat["courses"][3]["merged_into"] == 0  # pre-existing link survives
    assert "merged_into" not in cat["courses"][0]


def test_dedupe_reddit_keeps_hn_entry_with_reddit_keeper(monkeypatch):
    import canonicalize
    cat = {"courses": [{"id": 0, **c("Algo", "Coursera"), "origin": "reddit"},
                       {"id": 1, **c("Algo", "Coursera")}], "aliases": {}}
    monkeypatch.setattr(canonicalize, "structured", lambda *a, **k: ({"groups": [[0, 1]]}, 0.0))
    canonicalize.dedupe_reddit(cat, "key")
    assert "merged_into" not in cat["courses"][1]  # hn entry is never the duplicate
    assert cat["courses"][0]["merged_into"] == 1  # the Reddit entry joins the HN one


def test_dedupe_reddit_merges_reddit_entry_into_hn_whatever_the_order(monkeypatch):
    import canonicalize
    cat = {"courses": [{"id": 0, **c("Algo", "Coursera"), "origin": "reddit"},
                       {"id": 1, **c("Algo", "Coursera")},
                       {"id": 2, **c("Algo", "Coursera (Princeton)")}], "aliases": {}}
    monkeypatch.setattr(canonicalize, "structured", lambda *a, **k: ({"groups": [[0, 1, 2]]}, 0.0))
    canonicalize.dedupe_reddit(cat, "key")
    assert cat["courses"][0]["merged_into"] == 1
    assert "merged_into" not in cat["courses"][1] and "merged_into" not in cat["courses"][2]


# ---- main(): mapping runs and the CLI ---------------------------------------

def run_main(tmp_path, monkeypatch, argv, cat, reddit_courses=(), answer=None):
    import json

    import canonicalize
    import sources
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(cat), encoding="utf-8")
    fake = sources.Paths(*(tmp_path / n for n in ("c.jsonl", "p.json", "l.jsonl", "co.json", "t.json", "s.jsonl")))
    fake.courses.write_text(json.dumps(list(reddit_courses)), encoding="utf-8")
    calls = []

    def fake_structured(*a, **k):
        calls.append(a)
        return answer, 0.0

    monkeypatch.setattr(canonicalize, "CATALOG", catalog)
    monkeypatch.setattr(canonicalize, "paths", lambda s: fake)
    monkeypatch.setattr(canonicalize, "api_key", lambda: "k")
    monkeypatch.setattr(canonicalize, "structured", fake_structured)
    monkeypatch.setattr(sys, "argv", ["canonicalize.py", *argv])
    canonicalize.main()
    return json.loads(catalog.read_text(encoding="utf-8")), calls


def test_reddit_run_never_rewrites_an_hn_alias(tmp_path, monkeypatch):
    cat = {"courses": [{"id": 0, **c("CS50", "Harvard")}], "aliases": {"CS50|Harvard": 0}}
    comments = [{"id": "t1_a", "courses": [c("CS50", "Harvard"), c("CS50", "Harvard University")]},
                {"id": "t1_b", "courses": [c("CS50", "Harvard")]}]
    answer = {"items": [{"ref": 0, "match_id": None, "not_a_course": True, "name": "", "provider": ""}]}
    out, _ = run_main(tmp_path, monkeypatch, ["--source", "reddit"], cat, comments, answer)
    assert out["aliases"]["CS50|Harvard"] == 0
    assert out["aliases"]["CS50|Harvard University"] is None


def test_reddit_run_new_entry_leaves_hn_alias_alone(tmp_path, monkeypatch):
    cat = {"courses": [{"id": 0, **c("CS50", "Harvard")}], "aliases": {"CS50|Harvard": 0}}
    comments = [{"id": "t1_a", "courses": [c("CS50", "Harvard"), c("CS50", "Harvard University")]}]
    answer = {"items": [{"ref": 0, "match_id": None, "not_a_course": False, "name": "CS50x", "provider": "edX"}]}
    out, _ = run_main(tmp_path, monkeypatch, ["--source", "reddit"], cat, comments, answer)
    assert out["aliases"]["CS50|Harvard"] == 0
    assert out["aliases"]["CS50|Harvard University"] == 1 and out["courses"][1]["origin"] == "reddit"


def test_hn_wide_dedupe_refuses_once_reddit_entries_exist(tmp_path, monkeypatch, capsys):
    import pytest
    cat = {"courses": [{"id": 0, **c("A", "X")}, {"id": 1, **c("A", "X"), "origin": "reddit", "merged_into": 0}],
           "aliases": {}}
    with pytest.raises(SystemExit) as exc:
        run_main(tmp_path, monkeypatch, ["--dedupe"], cat, answer={"groups": []})
    assert "--dedupe-reddit" in str(exc.value)
    import json
    assert json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8")) == cat  # untouched


def test_hn_wide_dedupe_runs_without_reddit_entries(tmp_path, monkeypatch):
    cat = {"courses": [{"id": 0, **c("A", "X")}, {"id": 1, **c("B", "Y"), "merged_into": 0}], "aliases": {}}
    out, calls = run_main(tmp_path, monkeypatch, ["--dedupe"], cat, answer={"groups": []})
    assert len(calls) == 1 and "merged_into" not in out["courses"][1]  # re-run starts clean


def test_cli_rejects_bad_combinations(tmp_path, monkeypatch):
    import pytest
    cat = {"courses": [], "aliases": {}}
    for argv in (["--source", "reddit", "--dedupe"], ["--source", "lobsters"], ["--dedupe", "--dedupe-reddit"]):
        with pytest.raises(SystemExit) as exc:
            run_main(tmp_path, monkeypatch, argv, cat, answer={"groups": []})
        assert exc.value.code != 0


def test_cli_limit_is_positional(tmp_path, monkeypatch):
    cat = {"courses": [], "aliases": {}}
    comments = [{"id": "t1_a", "courses": [c("Alpha", "X")]}, {"id": "t1_b", "courses": [c("Beta", "Y")]}]
    answer = {"items": [{"ref": 0, "match_id": None, "not_a_course": False, "name": "", "provider": ""}]}
    out, calls = run_main(tmp_path, monkeypatch, ["--source", "reddit", "1"], cat, comments, answer)
    assert len(calls) == 1 and len(out["aliases"]) == 1
