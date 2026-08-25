# AI Usage

AI coding assistance was used selectively during development for implementation support, code review, debugging suggestions, and improving documentation clarity.

I defined the project scope, reviewed the dataset structure, selected the evidence schema and category-specific dimensions, implemented and tested the processing and ranking workflow, and reviewed the generated outputs.

The final system runs locally using supplied files and deterministic rules. It does not use an AI model at runtime. Matching decisions are based on explicit, traceable signals so that outputs can be reproduced and inspected.

I manually verified the run command, generated output formats, evidence references, recommendation flow, and follow-up re-ranking behavior. Media-derived observations are treated conservatively: lightweight local probes provide technical metadata such as dimensions, duration, orientation, brightness, and timestamps, while unsupported semantic conclusions remain marked as unknown or low confidence.

AI assistance was used as a development aid; all final implementation choices, submitted code, and output claims were reviewed by me.