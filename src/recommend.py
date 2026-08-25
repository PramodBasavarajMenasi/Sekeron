from __future__ import annotations

from .analyze_artists import classify_dimension
from .schemas import Brief, CapabilityRecord, RankedArtist


WEIGHTS = {
    "category_fit": 35.0,
    "demonstrated_evidence_fit": 30.0,
    "profile_claim_fit": 20.0,
    "format_style_fit": 10.0,
    "uncertainty_penalty": -15.0,
}


def recommend_for_brief(brief: Brief, artists: list[CapabilityRecord], top_n: int = 2) -> dict:
    ranked = sorted((score_artist(brief, artist) for artist in artists), key=lambda item: item.score, reverse=True)
    top = ranked[:top_n]
    return {
        "brief_id": brief.brief_id,
        "source_file": brief.source_file,
        "explicit_constraints": brief.explicit_constraints,
        "assumptions": brief.assumptions or ["No extra assumptions beyond the parsed brief"],
        "contradictions": brief.contradictions,
        "unknowns": brief.unknowns,
        "ranked_artists": [artist.__dict__ for artist in top],
        "improve_your_matches": improve_questions(brief),
        "expected_ranking_impact": "More category, format, budget, and deadline detail can change close rankings by reducing uncertainty penalties.",
    }


def score_artist(brief: Brief, artist: CapabilityRecord) -> RankedArtist:
    terms = set(brief.desired_terms)
    category_fit = 1.0 if brief.requested_category == artist.category else 0.0
    if not brief.requested_category:
        category_fit = inferred_category_fit(terms, artist)

    demonstrated_hits = 0
    evidence_reasons: list[str] = []
    for dimension, evidence_items in artist.demonstrated_capabilities.items():
        for evidence in evidence_items:
            if any(term in evidence.claim.lower() for term in terms):
                demonstrated_hits += 1
                evidence_reasons.append(f"{dimension}: {evidence.claim} ({evidence.source_file})")
                break
    demonstrated_fit = min(demonstrated_hits / max(len(terms), 1), 1.0)

    profile_text = " ".join(e.claim.lower() for e in artist.profile_claims)
    profile_hits = sum(1 for term in terms if term in profile_text)
    profile_fit = min(profile_hits / max(len(terms), 1), 1.0)

    format_terms = {"vertical", "reel", "social", "cafe", "live", "product", "event", "corporate"}
    format_hits = sum(1 for term in terms & format_terms if term in profile_text or any_media_claim(artist, term))
    format_fit = min(format_hits / max(len(terms & format_terms), 1), 1.0) if terms & format_terms else 0.5

    uncertainty = min((len(artist.unknowns) + len(brief.unknowns)) / 8, 1.0)
    breakdown = {
        "category_fit": round(category_fit * WEIGHTS["category_fit"], 2),
        "demonstrated_evidence_fit": round(demonstrated_fit * WEIGHTS["demonstrated_evidence_fit"], 2),
        "profile_claim_fit": round(profile_fit * WEIGHTS["profile_claim_fit"], 2),
        "format_style_fit": round(format_fit * WEIGHTS["format_style_fit"], 2),
        "uncertainty_penalty": round(uncertainty * WEIGHTS["uncertainty_penalty"], 2),
    }
    score = round(sum(breakdown.values()), 2)

    reasons = []
    if category_fit:
        reasons.append(f"Category fit: {artist.category}")
    reasons.extend(evidence_reasons[:3])
    if profile_hits:
        reasons.append(f"Profile claims overlap with requested terms: {profile_hits} match(es)")
    if brief.extracted_values.get("budget"):
        reasons.append(f"Budget considered from brief: {brief.extracted_values['budget']}")
    if brief.extracted_values.get("date"):
        tradeoff_context = f"Date/timeline considered from brief: {brief.extracted_values['date']}"
    else:
        tradeoff_context = ""
    if not reasons:
        reasons.append("Ranked mainly because alternatives had weaker category or evidence fit")

    tradeoffs = []
    if tradeoff_context:
        tradeoffs.append(tradeoff_context)
    if artist.unknowns:
        tradeoffs.append("; ".join(artist.unknowns[:2]))
    if artist.confidence == "low":
        tradeoffs.append("Low confidence because media observations are placeholders or evidence is sparse")
    if brief.requested_category and brief.requested_category != artist.category:
        tradeoffs.append(f"Category mismatch: brief asks for {brief.requested_category}")

    return RankedArtist(
        artist_id=artist.artist_id,
        name=artist.name,
        category=artist.category,
        score=score,
        reasons=reasons,
        tradeoffs=tradeoffs[:3],
        score_breakdown=breakdown,
    )


def inferred_category_fit(terms: set[str], artist: CapabilityRecord) -> float:
    category_terms = {
        "photographers": {"photo", "photography", "shoot", "portrait", "product", "event"},
        "musicians": {"music", "musician", "song", "live", "cafe", "acoustic", "ambient"},
        "video_editors": {"video", "editor", "reel", "vertical", "motion", "social"},
    }
    return min(len(terms & category_terms.get(artist.category, set())) / 2, 1.0)


def any_media_claim(artist: CapabilityRecord, term: str) -> bool:
    for evidence_items in artist.demonstrated_capabilities.values():
        if any(term in evidence.claim.lower() for evidence in evidence_items):
            return True
    return False


def improve_questions(brief: Brief) -> list[dict[str, str]]:
    questions = []
    if "Budget is not specified" in brief.unknowns:
        questions.append({
            "question": "What budget or rate range should the match optimize for?",
            "expected_ranking_impact": "Could favor artists with explicit matching profile claims and penalize otherwise good matches with unknown commercial fit.",
        })
    if "Timeline is not specified" in brief.unknowns:
        questions.append({
            "question": "What delivery date or event date should availability be checked against?",
            "expected_ranking_impact": "Would not infer availability, but would highlight that the current ranking ignores scheduling risk.",
        })
    if not questions:
        questions.append({
            "question": "Which capability matters most if two artists are close: style match, format, or category specialization?",
            "expected_ranking_impact": "Would shift weight toward the selected capability and can swap close-ranked artists.",
        })
    return questions[:2]
