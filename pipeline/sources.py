"""Per-source data layout: Hacker News and Reddit are processed and ranked separately."""

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SOURCES = ("hn", "reddit")

SUBREDDITS = (
    "Entrepreneur", "startups", "smallbusiness", "SaaS", "indiehackers", "EntrepreneurRideAlong",
    "programming", "ExperiencedDevs", "webdev", "learnprogramming", "Python", "selfhosted",
    "MachineLearning", "LocalLLaMA", "artificial", "ChatGPT", "ClaudeAI", "learnmachinelearning",
    "productivity", "getdisciplined", "Notion", "ObsidianMD", "PKMS", "bujo",
    "marketing", "PPC", "SEO", "bigseo", "socialmedia", "Emailmarketing",
)


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
