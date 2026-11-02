import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from discover_images import title_matches  # noqa: E402


def c(name):
    return {"name": name, "provider": "x"}


def test_matching_page_title_is_accepted():
    assert title_matches(c("Learning How to Learn: Powerful mental tools to help you master tough subjects"),
                         "Learning How to Learn: Powerful mental tools to help you master tough subjects | Coursera")
    assert title_matches(c("Functional Programming Principles in Scala"),
                         "Functional Programming Principles in Scala | Coursera")


def test_course_code_is_enough():
    assert title_matches(c("6.006 Introduction to Algorithms"), "Introduction to Algorithms | Electrical Engineering | 6.006")


def test_broader_page_sharing_some_words_is_rejected():
    assert not title_matches(c("Artificial Intelligence for Robotics"), "School of Artificial Intelligence | Udacity")


def test_unrelated_page_is_rejected():
    assert not title_matches(c("Cryptography I"), "Coursera | Online Courses From Top Universities")
    assert not title_matches(c("Functional Programming Principles in Scala"), "Page not found")
    assert not title_matches(c("CS229 Machine Learning"), "CS231n Convolutional Neural Networks")
