# Evidence-Led Artist Recommendation System

Small Python 3 project for an AI internship assessment. It reads local artist folders, builds evidence-backed artist capability records, recommends top matches for hirer briefs, and reranks one match after a follow-up update.

## What It Produces

Outputs are written to `outputs/`:

- `artist_intelligence.jsonl`
- `recommendations.json`
- `updated_recommendation.json`

## Run

Create or repair the virtual environment, then install the small media-probing dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

```bash
python -m src.main --data "Data set" --out outputs
```

If your machine uses a different Python launcher:

```bash
python3 -m src.main --data "Data set" --out outputs
py -3 -m src.main --data "Data set" --out outputs
```

The code also supports the prompt's generic structure:

```text
data/
  artists/
  briefs/
  follow_up/updated_brief.txt
```

and the supplied structure:

```text
Data set/
  artist_profiles/
  hirer_conversations/
  follow_up_update/
```

## Approach

1. Build an artist inventory before analysis.
2. Extract profile claims from `.txt`, `.md`, `.rtf`, and `.docx` files.
3. Detect image, audio, video, profile, and unsupported file types.
4. Sample media selectively with a three-layer local process:
   - metadata: image dimensions/brightness, audio duration/bitrate/sample rate, video duration/resolution/fps
   - sampling: images by first/middle/last/descriptive names; audio/video at beginning/middle/end
   - understanding: filename cues or manual review only; no unsupported semantic claims
5. Create category-specific capability records:
   - photographers: subject, style, lighting, composition, context
   - musicians: genre, mood, instrumentation, vocal production, format
   - video editors: pacing, storytelling, transitions, motion graphics, color/sound, platform format
6. Score artists with deterministic weighted rules:
   - category fit
   - demonstrated evidence fit
   - profile claim fit
   - format/style fit
   - uncertainty penalty

## Important Limits

This project does not scrape the web, deploy an app, train a model, or infer personal traits such as reliability, punctuality, character, popularity, or professionalism. Media-derived observations are limited to local file probes such as dimensions, duration, orientation, brightness and sampled timestamps. They are marked low confidence unless human review confirms semantic content.

## Evaluation

Basic checks:

- `artist_intelligence.jsonl` should contain 15 records.
- `recommendations.json` should contain 4 briefs, each with 2 ranked artists.
- `updated_recommendation.json` should include original ranking, follow-up information, updated ranking, and a change explanation.

Reported build time: about 2 hours for the first working version, excluding local dataset review.

## Requirements

The project uses Python standard library modules, `pathlib`, `dataclasses`, and three local media-inspection libraries listed in `requirements.txt`:

- Pillow for image dimensions/orientation/brightness
- OpenCV for video resolution, fps, duration and sampled frame positions
- Mutagen for audio duration, bitrate, sample rate and channels where available
