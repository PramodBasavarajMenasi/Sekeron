from __future__ import annotations

import re
from pathlib import Path

from .ingest import briefs_root
from .schemas import Brief


CATEGORY_TERMS = {
    "photographers": ["photo", "photography", "photographer", "shoot", "portrait", "images"],
    "musicians": ["music", "musician", "song", "live", "cafe", "band", "singer", "audio"],
    "video_editors": ["video", "editor", "reel", "vertical", "edit", "motion", "shorts"],
}

CONSTRAINT_MARKERS = ["must", "need", "required", "budget", "deadline", "format", "vertical", "date", "location"]
BUDGET_PATTERN = re.compile(
    r"(?:\u20b9|rs\.?|inr|\$|usd)\s*\d+(?:,\d{2,3})*(?:\.\d+)?\s*(?:k|lakh|lakhs|lac|lacs|crore|cr)?"
    r"|\b\d+(?:\.\d+)?\s*(?:k|lakh|lakhs|lac|lacs|crore|cr)\b",
    re.IGNORECASE,
)
PLAIN_BUDGET_PATTERN = re.compile(
    r"\b(?:budget|rate|price)\b[^\n.]{0,40}?\b\d+(?:,\d{2,3})*(?:\.\d+)?\b",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(
    r"\b(?:today|tomorrow|tonight|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month)|"
    r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
    r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b",
    re.IGNORECASE,
)


def parse_all_briefs(data_root: Path) -> list[Brief]:
    root = briefs_root(data_root)
    return [parse_brief(path) for path in sorted(root.glob("*.txt"))]


def parse_brief(path: Path) -> Brief:
    text = path.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()
    category = detect_requested_category(lower)
    constraints = sentence_matches(text, CONSTRAINT_MARKERS)
    extracted_values = extract_constraint_values(text)
    constraints = add_extracted_value_constraints(constraints, extracted_values)
    desired_terms = extract_desired_terms(lower)
    unknowns = []
    assumptions = []
    if not category:
        unknowns.append("Requested artist category is not explicit")
        assumptions.append("Use keyword overlap to infer the most likely category")
    if "budget" not in extracted_values and not any(word in lower for word in ["budget", "rate", "price"]):
        unknowns.append("Budget is not specified")
    if "date" not in extracted_values and not any(word in lower for word in ["date", "deadline", "tomorrow", "week", "month"]):
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
        extracted_values=extracted_values,
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


def extract_constraint_values(text: str) -> dict[str, str]:
    extracted = {}
    budgets = extract_budget_values(text)
    dates = unique_matches(DATE_PATTERN.findall(text))
    if budgets:
        extracted["budget"] = ", ".join(budgets)
    if dates:
        extracted["date"] = ", ".join(dates)
    return extracted


def add_extracted_value_constraints(constraints: list[str], extracted_values: dict[str, str]) -> list[str]:
    result = list(constraints)
    if "budget" in extracted_values and not any(extracted_values["budget"] in item for item in result):
        result.append(f"Extracted budget value(s): {extracted_values['budget']}")
    if "date" in extracted_values and not any(extracted_values["date"] in item for item in result):
        result.append(f"Extracted date/timeline value(s): {extracted_values['date']}")
    return result


def extract_budget_values(text: str) -> list[str]:
    values = unique_matches(BUDGET_PATTERN.findall(text))
    for match in PLAIN_BUDGET_PATTERN.findall(text):
        number = re.search(r"\d+(?:,\d{2,3})*(?:\.\d+)?", match)
        if number:
            values.append(number.group(0))
    return unique_matches(values)


def unique_matches(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = " ".join(value.strip().split())
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def normalized_budget_values(lower: str) -> set[str]:
    values = set()
    for raw in extract_budget_values(lower):
        cleaned = raw.strip().lower().replace(" ", "")
        cleaned = cleaned.replace(",", "")
        cleaned = re.sub(r"^(\u20b9|rs\.?|inr|usd|\$)", "", cleaned)
        values.add(cleaned)
    return values


def find_contradictions(lower: str) -> list[str]:
    contradictions = []
    if "no vocals" in lower and ("singer" in lower or "vocals" in lower):
        contradictions.append("Brief mentions no vocals but also asks for vocals/singer")
    if "horizontal" in lower and "vertical" in lower:
        contradictions.append("Brief mentions both horizontal and vertical format")
    budgets = normalized_budget_values(lower)
    if len(budgets) > 1:
        contradictions.append("Brief mentions multiple different budget values")
    return contradictions
