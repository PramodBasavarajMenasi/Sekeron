# Decision Note

## Problem Framing

The assessment asks for an evidence-led system, not a production marketplace or recommendation model. I therefore optimized for clarity, defensibility, and local reproducibility.

## Design Choices

- Deterministic rules are used instead of model training.
- Artist inventory is created first so missing, unsupported, and damaged files are visible.
- Profile claims are separated from demonstrated capabilities.
- Media analysis is selective and conservative, using a three-layer process: metadata, sampling and filename/manual understanding.
- Media-derived claims cite source files plus image index or timestamp.
- Low confidence is used when the system has metadata/probe evidence but no human semantic review.
- The recommendation output includes assumptions, contradictions, unknowns, tradeoffs, and questions that would improve matching.

## Scoring

The score is a weighted sum:

- category fit: 35
- demonstrated evidence fit: 30
- profile claim fit: 20
- format/style fit: 10
- uncertainty penalty: -15

This keeps rankings explainable. A weaker artist can still rank if the brief is incomplete, but uncertainty is surfaced rather than hidden.

## Safety Boundaries

The system never infers reliability, punctuality, character, popularity, or professionalism from portfolio media. It only records observable or text-supported capability evidence.

## Future Improvements

- Add stronger human-reviewed visual/audio annotations for semantic claims.
- Add a manually reviewed observation file for higher-confidence visual/audio annotations.
- Add unit tests for scoring edge cases and malformed inputs.

Reported build time: about 2 hours for the first working version.
