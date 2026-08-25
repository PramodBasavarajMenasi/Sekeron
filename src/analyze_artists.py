from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .ingest import detect_file_type, read_text
from .media_probe import probe_audio, probe_image, probe_video
from .schemas import CATEGORY_DIMENSIONS, ArtistInventory, CapabilityRecord, Evidence


KEYWORDS = {
    "photographers": {
        "subject": ["portrait", "product", "skincare", "event", "leadership", "cafe", "wedding", "fashion", "street"],
        "style": ["editorial", "candid", "documentary", "minimal", "lifestyle", "cinematic", "clean"],
        "lighting": ["natural light", "studio", "flash", "soft", "low light", "balanced light", "bright", "golden hour"],
        "composition": ["close-up", "wide", "detail", "flatlay", "symmetry", "frame", "still image", "vertical", "horizontal", "square"],
        "context": ["brand", "social", "corporate", "conference", "launch", "outdoor", "portfolio"],
    },
    "musicians": {
        "genre": ["acoustic", "folk", "electronic", "jazz", "pop", "rock", "ballad", "downtempo"],
        "mood": ["calm", "upbeat", "warm", "ambient", "romantic", "energetic", "chill"],
        "instrumentation": ["guitar", "piano", "synth", "drums", "vocals", "acoustic"],
        "vocal_production": ["male vocal", "female vocal", "vocals", "instrumental", "harmony"],
        "format": ["live", "cafe", "rehearsal", "demo", "set", "performance"],
    },
    "video_editors": {
        "pacing": ["fast", "slow", "dynamic", "snappy", "reel", "vlog"],
        "storytelling": ["story", "bts", "event", "brand", "testimonial", "narrative"],
        "transitions": ["transition", "cut", "montage"],
        "motion_graphics": ["graphics", "text", "titles", "animation"],
        "color_sound": ["color", "sound", "music", "cinematic"],
        "platform_format": ["vertical", "instagram", "reel", "youtube", "short", "social", "video edit", "video-edit", "portfolio format"],
    },
}


def analyze_artists(inventories: list[ArtistInventory]) -> list[CapabilityRecord]:
    return [analyze_artist(inventory) for inventory in inventories]


def analyze_artist(inventory: ArtistInventory) -> CapabilityRecord:
    profile_texts: list[tuple[Path, str]] = []
    damaged = list(inventory.damaged_files)
    for profile in inventory.profile_files:
        path = Path(profile)
        text, error = read_text(path)
        if error:
            damaged.append(error)
        if text.strip():
            profile_texts.append((path, text))

    profile_claims = extract_profile_claims(inventory.category, profile_texts)
    demonstrated = defaultdict(list)

    media_evidence, media_selection = sample_media_observations(inventory)
    for evidence in media_evidence:
        dimension = classify_dimension(inventory.category, evidence.claim)
        if dimension:
            demonstrated[dimension].append(evidence)

    dimensions = CATEGORY_DIMENSIONS.get(inventory.category, [])
    unknowns = [f"No evidence found for {dimension}" for dimension in dimensions if not demonstrated.get(dimension)]
    unknowns.extend(damaged[:3])
    confidence = confidence_label(profile_claims, demonstrated, damaged)

    return CapabilityRecord(
        artist_id=inventory.artist_id,
        name=inventory.name,
        category=inventory.category,
        capability_assessment=summarize_capability(inventory.category, demonstrated, profile_claims),
        profile_claims=profile_claims,
        demonstrated_capabilities={dimension: demonstrated.get(dimension, []) for dimension in dimensions},
        media_selection=media_selection,
        unknowns=unknowns,
        confidence=confidence,
        inventory=inventory,
    )


def extract_profile_claims(category: str, profile_texts: list[tuple[Path, str]]) -> list[Evidence]:
    claims: list[Evidence] = []
    terms = [term for values in KEYWORDS.get(category, {}).values() for term in values]
    for path, text in profile_texts:
        lines = [line.strip(" -\t") for line in text.splitlines() if line.strip()]
        for line in lines:
            lower = line.lower()
            if any(term in lower for term in terms):
                claims.append(Evidence(str(path), "profile_text", line[:240], confidence="medium"))
        if not claims and text.strip():
            claims.append(Evidence(str(path), "profile_text", text.strip().replace("\n", " ")[:240], confidence="low"))
    return claims[:12]


def sample_media_observations(inventory: ArtistInventory) -> tuple[list[Evidence], dict]:
    media = [Path(path) for path in inventory.media_files]
    images = [p for p in media if detect_file_type(p) == "image"]
    audio = [p for p in media if detect_file_type(p) == "audio"]
    video = [p for p in media if detect_file_type(p) == "video"]
    evidence: list[Evidence] = []
    selected_images = select_images(images)

    for idx, path in enumerate(selected_images, start=1):
        evidence.append(probe_image(path, idx, inventory.category))
        filename_claim = filename_observation(inventory.category, path, "image filename")
        if "filename suggests" in filename_claim:
            evidence.append(Evidence(str(path), "media_filename", filename_claim, image_index=idx, confidence="low", layer="understanding"))
    for path in audio:
        evidence.extend(probe_audio(path))
        filename_claim = filename_observation(inventory.category, path, "audio filename")
        if "filename suggests" in filename_claim:
            evidence.append(Evidence(str(path), "media_filename", filename_claim, timestamp="filename", confidence="low", layer="understanding"))
    for path in video:
        evidence.extend(probe_video(path, inventory.category))
        filename_claim = filename_observation(inventory.category, path, "video filename")
        if "filename suggests" in filename_claim:
            evidence.append(Evidence(str(path), "media_filename", filename_claim, timestamp="filename", confidence="low", layer="understanding"))
    strategy = {
        "images": {
            "total": len(images),
            "selected": [str(path) for path in selected_images],
            "skipped_count": max(len(images) - len(selected_images), 0),
            "layers": ["metadata", "selective_sampling", "filename_or_manual_understanding"],
            "why": "All images are selected for small folders; larger folders use first/middle/last plus descriptive filenames.",
        },
        "audio": {
            "total": len(audio),
            "selected": [str(path) for path in audio],
            "timestamps": ["00:00", "middle", "end"],
            "layers": ["metadata", "selective_sampling", "filename_or_manual_understanding"],
            "why": "Audio metadata is read and beginning/middle/end positions are sampled instead of every second.",
        },
        "video": {
            "total": len(video),
            "selected": [str(path) for path in video],
            "timestamps": ["00:00", "middle", "end"],
            "layers": ["metadata", "selective_sampling", "filename_or_manual_understanding"],
            "why": "Video metadata is read and beginning/middle/end frame positions are sampled instead of every frame.",
        },
    }
    return evidence[:24], strategy


def select_images(paths: list[Path]) -> list[Path]:
    if len(paths) <= 8:
        return paths
    picks = {0, len(paths) // 2, len(paths) - 1}
    descriptive = sorted(range(len(paths)), key=lambda i: len(paths[i].stem), reverse=True)[:5]
    picks.update(descriptive)
    return [paths[i] for i in sorted(picks)]


def filename_observation(category: str, path: Path, prefix: str) -> str:
    name = path.stem.replace("_", " ").replace("-", " ").lower()
    matched = []
    for terms in KEYWORDS.get(category, {}).values():
        matched.extend(term for term in terms if term in name)
    if matched:
        return f"{prefix}: filename suggests {', '.join(sorted(set(matched)))}; requires human verification"
    return f"{prefix}: sampled for human-verifiable review; no semantic claim inferred from media content"


def classify_dimension(category: str, text: str) -> str | None:
    lower = text.lower().replace("-", " ")
    for dimension, terms in KEYWORDS.get(category, {}).items():
        if any(term.replace("-", " ") in lower for term in terms):
            return dimension
    return None


def confidence_label(profile_claims: list[Evidence], demonstrated: dict[str, list[Evidence]], damaged: list[str]) -> str:
    covered = sum(1 for values in demonstrated.values() if values)
    if damaged:
        return "low"
    if covered >= 4 and len(profile_claims) >= 3:
        return "medium"
    return "low"


def summarize_capability(category: str, demonstrated: dict[str, list[Evidence]], profile_claims: list[Evidence]) -> str:
    covered = [dimension for dimension, evidence in demonstrated.items() if evidence]
    if covered:
        return f"Evidence-backed {category} record covers: {', '.join(covered)}."
    if profile_claims:
        return "Profile text contains claims, but supplied media did not produce capability evidence under the conservative placeholder rules."
    return "Insufficient readable evidence to assess capabilities beyond inventory metadata."
