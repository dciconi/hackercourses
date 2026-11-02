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
    assert users == {"someone"}


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
