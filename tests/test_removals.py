import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import removals  # noqa: E402


def write(tmp_path, text):
    p = tmp_path / "removals.txt"
    p.write_text(text, encoding="utf-8")
    return p


def test_ids_users_and_notes(tmp_path):
    ids, users = removals.load(write(tmp_path, "# header\n41709040  # issue #3\nuser:SomeOne\n\n"))
    assert ids == {41709040}
    assert users == {("hn", "someone")}


def test_removed_matches_id_or_user_case_insensitively(tmp_path):
    ids, users = removals.load(write(tmp_path, "123\nuser:alice\n"))
    assert removals.removed({"id": 123, "by": "bob"}, ids, users)
    assert removals.removed({"id": 9, "by": "Alice"}, ids, users)
    assert not removals.removed({"id": 9, "by": "bob"}, ids, users)


def test_unreadable_line_fails_loudly(tmp_path):
    with pytest.raises(ValueError):
        removals.load(write(tmp_path, "https://news.ycombinator.com/item?id=123\n"))


def test_missing_file_removes_nothing(tmp_path):
    assert removals.load(tmp_path / "absent.txt") == (set(), set())


def test_reddit_ids_and_users(tmp_path):
    ids, users = removals.load(write(tmp_path, "reddit:abc\nreddit:t1_XyZ9  # note\nreddit-user:SomeOne\n"))
    assert ids == {"t1_abc", "t1_xyz9"}
    assert users == {("reddit", "someone")}
    assert removals.removed({"id": "t1_abc", "src": "reddit", "by": "x"}, ids, users)
    assert removals.removed({"id": "t1_q", "src": "reddit", "by": "SOMEONE"}, ids, users)
    assert not removals.removed({"id": "t1_q", "src": "reddit", "by": "other"}, ids, users)


def test_hn_user_does_not_remove_same_name_on_reddit(tmp_path):
    ids, users = removals.load(write(tmp_path, "user:alice\n"))
    assert removals.removed({"id": 1, "by": "alice"}, ids, users)
    assert not removals.removed({"id": "t1_a", "src": "reddit", "by": "alice"}, ids, users)
    ids, users = removals.load(write(tmp_path, "reddit-user:alice\n"))
    assert not removals.removed({"id": 1, "by": "alice"}, ids, users)


@pytest.mark.parametrize("line", ["reddit:", "reddit:not an id", "reddit:t1_", "reddit-user:", "reddit:t3_abc"])
def test_garbage_reddit_lines_fail(tmp_path, line):
    with pytest.raises(ValueError):
        removals.load(write(tmp_path, line + "\n"))
