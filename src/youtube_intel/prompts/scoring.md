---
prompt_version: scoring-prompt-v1
schema_version: score-result-v1
---

You score the learning and product value of a video using only the supplied
metadata and sampled canonical transcript. Return exactly one JSON object that
matches the requested schema. Do not include Markdown, explanations outside the
JSON object, invented facts, or fields that the schema does not allow.

`should_summarize` is your recommendation only. The application applies its own
threshold policy and may make a different final decision.

Input:

{{SCORING_INPUT_JSON}}
