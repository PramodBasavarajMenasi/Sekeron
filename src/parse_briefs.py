from __future__ import annotations

from pathlib import Path

from .ingest import briefs_root
from .schemas import Brief


CATEGORY_TERMS = {
    "photographers": ["photo", "photography", "photographer", "shoot", "portrait", "images"],
    "musicians": ["music", "musician", "song", "live", "cafe", "band", "singer", "audio"],
    "video_editors": ["video", "editor", "reel", "vertical", "edit", "motion", "shorts"],
}

CONSTRAINT_MARKERS = ["must", "need", "required", "budget", "deadline", "format", "vertical", "date", "location"]


def parse_all_briefs(data_root: Path) -> list[Brief]:
    root = briefs_root(data_root)
    return [parse_brief(path) for path in sorted(root.glob("*.txt"))]


def parse_brief(path: Path) -> Brief:
    text = path.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()
    category = detect_requested_category(lower)
    constraints = sentence_matches(text, CONSTRAINT_MARKERS)
    desired_terms = extract_desired_terms(lower)
    unknowns = []
    assumptions = []
    if not category:
        unknowns.append("Requested artist category is not explicit")
        assumptions.append("Use keyword overlap to infer the most likely category")
    if not any(word in lower for word in ["budget", "rate", "price"]):
        unknowns.append("Budget is not specified")
    if not any(word in lower for word in ["date", "deadline", "tomorrow", "week", "month"]):
        unknowns.append("Timeline is not specified")
    contradictions = find_contradictions(lower)
    return Brief(
        brief_id=path.stem,
        source_file=str(path),
        raw_text=text,
        requested_category=category,
        explicit_constraints=constraints[:6],
        desired_terms=desired_terms,
        assumptions=assumptions,
        unknowns=unknowns,
        contradictions=contradictions,
    )


def detect_requested_category(lower: str) -> str | None:
    scores = {
        category: sum(1 for term in terms if term in lower)
        for category, terms in CATEGORY_TERMS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] else None


def sentence_matches(text: str, markers: list[str]) -> list[str]:
    chunks = text.replace("\n", ". ").split(".")
    return [chunk.strip() for chunk in chunks if chunk.strip() and any(marker in chunk.lower() for marker in markers)]


def extract_desired_terms(lower: str) -> list[str]:
    vocabulary = sorted({term for terms in CATEGORY_TERMS.values() for term in terms} | {
        "acoustic", "ambient", "brand", "cafe", "candid", "cinematic", "corporate", "event",
        "fast", "leadership", "lifestyle", "natural light", "product", "reel", "skincare",
        "social", "upbeat", "vertical", "warm",
    })
    return [term for term in vocabulary if term in lower]


def find_contradictions(lower: str) -> list[str]:
    contradictions = []
    if "no vocals" in lower and ("singer" in lower or "vocals" in lower):
        contradictions.append("Brief mentions no vocals but also asks for vocals/singer")
    if "horizontal" in lower and "vertical" in lower:
        contradictions.append("Brief mentions both horizontal and vertical format")
    return contradictions
