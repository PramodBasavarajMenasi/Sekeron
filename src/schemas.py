from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


CATEGORY_DIMENSIONS = {
    "photographers": ["subject", "style", "lighting", "composition", "context"],
    "musicians": ["genre", "mood", "instrumentation", "vocal_production", "format"],
    "video_editors": [
        "pacing",
        "storytelling",
        "transitions",
        "motion_graphics",
        "color_sound",
        "platform_format",
    ],
}


@dataclass
class Evidence:
    source_file: str
    kind: str
    claim: str
    image_index: int | None = None
    timestamp: str | None = None
    confidence: str = "low"
    layer: str = "understanding"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtistInventory:
    artist_id: str
    name: str
    category: str
    folder: str
    profile_files: list[str] = field(default_factory=list)
    media_files: list[str] = field(default_factory=list)
    damaged_files: list[str] = field(default_factory=list)


@dataclass
class CapabilityRecord:
    artist_id: str
    name: str
    category: str
    capability_assessment: str
    profile_claims: list[Evidence]
    demonstrated_capabilities: dict[str, list[Evidence]]
    media_selection: dict[str, Any]
    unknowns: list[str]
    confidence: str
    inventory: ArtistInventory


@dataclass
class Brief:
    brief_id: str
    source_file: str
    raw_text: str
    requested_category: str | None
    explicit_constraints: list[str]
    desired_terms: list[str]
    assumptions: list[str]
    unknowns: list[str]
    contradictions: list[str]
    extracted_values: dict[str, str] = field(default_factory=dict)


@dataclass
class RankedArtist:
    artist_id: str
    name: str
    category: str
    score: float
    reasons: list[str]
    tradeoffs: list[str]
    score_breakdown: dict[str, float]


def to_plain(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    return value
