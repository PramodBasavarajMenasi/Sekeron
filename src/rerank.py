from __future__ import annotations

from pathlib import Path

from .parse_briefs import parse_brief
from .recommend import recommend_for_brief
from .schemas import CapabilityRecord


def rerank_with_follow_up(
    original_recommendations: dict,
    follow_up_path: Path | None,
    artists: list[CapabilityRecord],
) -> dict:
    if follow_up_path is None or not follow_up_path.exists():
        return {
            "original_ranking": original_recommendations,
            "follow_up_information": "No follow-up file found",
            "updated_ranking": original_recommendations,
            "what_changed_and_why": ["No changes were applied because no follow-up update was available."],
        }

    follow_up_brief = parse_brief(follow_up_path)
    target = choose_original_brief(original_recommendations, follow_up_brief)
    combined = follow_up_brief
    if target:
        combined.raw_text = target.get("source_file", "") + "\n" + combined.raw_text
        combined.explicit_constraints = list(dict.fromkeys(target.get("explicit_constraints", []) + combined.explicit_constraints))
        combined.unknowns = [u for u in combined.unknowns if u not in target.get("unknowns", [])]
        combined.assumptions = list(dict.fromkeys(target.get("assumptions", []) + combined.assumptions))

    updated = recommend_for_brief(combined, artists)
    return {
        "original_ranking": target or original_recommendations,
        "follow_up_information": {
            "source_file": str(follow_up_path),
            "explicit_constraints": follow_up_brief.explicit_constraints,
            "desired_terms": follow_up_brief.desired_terms,
        },
        "updated_ranking": updated,
        "what_changed_and_why": explain_changes(target, updated, follow_up_brief),
    }


def choose_original_brief(original: dict, follow_up) -> dict | None:
    recommendations = original.get("recommendations", [])
    if not recommendations:
        return None
    if "cafe" in follow_up.raw_text.lower():
        for recommendation in recommendations:
            if "cafe" in recommendation.get("brief_id", "").lower() or "cafe" in " ".join(recommendation.get("explicit_constraints", [])).lower():
                return recommendation
    return recommendations[0]


def explain_changes(original: dict | None, updated: dict, follow_up) -> list[str]:
    if not original:
        return ["Follow-up was scored as a standalone brief because no original recommendation was available."]
    before = [a["artist_id"] for a in original.get("ranked_artists", [])]
    after = [a["artist_id"] for a in updated.get("ranked_artists", [])]
    changes = [f"Original top 2: {before}; updated top 2: {after}."]
    if before != after:
        changes.append("Ranking changed because follow-up terms and constraints altered keyword overlap and uncertainty.")
    else:
        changes.append("Ranking stayed stable; the same artists remained strongest under the added follow-up information.")
    if follow_up.explicit_constraints:
        changes.append(f"New explicit constraints considered: {'; '.join(follow_up.explicit_constraints[:3])}")
    return changes
