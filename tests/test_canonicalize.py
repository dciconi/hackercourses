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
