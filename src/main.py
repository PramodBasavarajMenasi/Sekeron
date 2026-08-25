from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .analyze_artists import analyze_artists
from .ingest import build_artist_inventory, follow_up_file, resolve_dataset_root
from .parse_briefs import parse_all_briefs
from .recommend import recommend_for_brief
from .rerank import rerank_with_follow_up


def main() -> None:
    parser = argparse.ArgumentParser(description="Build evidence-led artist recommendations.")
    parser.add_argument("--data", default="Data set", help="Path to local dataset folder")
    parser.add_argument("--out", default="outputs", help="Directory for JSON/JSONL outputs")
    args = parser.parse_args()

    data_root = resolve_dataset_root(args.data)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    inventories = build_artist_inventory(data_root)
    artists = analyze_artists(inventories)
    briefs = parse_all_briefs(data_root)

    write_jsonl(out_dir / "artist_intelligence.jsonl", [asdict(artist) for artist in artists])

    recommendations = {
        "dataset_root": str(data_root),
        "recommendations": [recommend_for_brief(brief, artists) for brief in briefs],
    }
    write_json(out_dir / "recommendations.json", recommendations)

    updated = rerank_with_follow_up(recommendations, follow_up_file(data_root), artists)
    write_json(out_dir / "updated_recommendation.json", updated)

    print(f"Wrote outputs to {out_dir.resolve()}")


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
