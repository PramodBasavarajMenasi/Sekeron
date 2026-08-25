# AI Usage

AI assistance was used to design and generate this codebase, documentation, and deterministic matching approach.

The system itself does not call an AI model at runtime. It uses local files only and deterministic keyword/rule scoring so that outputs are explainable and reproducible.

Human review is still required for semantic media interpretation. The code uses lightweight local probes for dimensions, duration, orientation, brightness and timestamps, then marks those media-derived observations low confidence unless directly verifiable.
