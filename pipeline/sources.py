"""Per-source data layout: Hacker News and Reddit are processed and ranked separately."""

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SOURCES = ("hn", "reddit")

SUBREDDITS = (
    "Entrepreneur", "startups", "smallbusiness", "SaaS", "indiehackers", "EntrepreneurRideAlong",
    "programming", "ExperiencedDevs", "webdev", "learnprogramming", "Python",
    "MachineLearning", "LocalLLaMA", "artificial", "ChatGPT", "ClaudeAI", "learnmachinelearning",
    "productivity", "getdisciplined", "Notion", "PKMS",
    "marketing", "PPC", "SEO",
)

# Dropped after the 2021-2023 pilot (owner decision, 2026-11-02): bujo, socialmedia, bigseo,
# ObsidianMD, selfhosted, Emailmarketing. classify.py ignores their rows if they are still in the data.


@dataclass(frozen=True)
class Paths:
    candidates: Path
    pool: Path
    labels: Path
    courses: Path
    threads: Path
    summaries: Path


def paths(source: str) -> Paths:
    if source not in SOURCES:
        raise ValueError(f"unknown source {source!r}")
    d = DATA if source == "hn" else DATA / source
    return Paths(d / "candidates.jsonl", d / "pool.json", d / "llm_labels.jsonl",
                 d / "courses.json", d / "threads.json", d / "summaries.jsonl")
