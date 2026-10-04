# Phase 9R bounded remediation plan

Owner: continuous sole executor. Baseline 0a0eef4b2c5f321f46b2c58ed2535d521af05b5d.
Worktree chatgpt/v1x-acoustic-remediation; schema 32; DA NONE.
Only existing exact large-v3-turbo revision a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb,
mlx-whisper 0.4.3 / MLX 0.32.0. No downloads, installs, upgrades or cloud calls.

## Fixed matrix, frozen before candidate execution

A: whole input, condition_on_previous_text true (unchanged Phase 9 baseline).
B: whole input, condition_on_previous_text false.
C: contiguous 25-second PCM source chunks, condition_on_previous_text true.
D: contiguous 25-second PCM source chunks, condition_on_previous_text false.
All other decoding options remain frozen. No per-sample changes. No expansion.

Chunks partition mono16k samples at integer multiples of 400000 frames. Last
chunk is shorter. Overlap zero; no deduplication, trimming, fuzzy merging or text
editing. Offsets are exact source frame / 16000. Validate local cues first,
then add source offsets and validate the entire merged result. Preserve all
speech bytes exactly once. A partial failure invalidates the complete attempt.
No cross-chunk prompt. SDK ModelHolder reuses one model for the logical job.
The zero-overlap policy must demonstrate acoustic boundary accuracy; contiguous
PCM alone does not prove transcription quality. If it fails, retain failure.

## Ordered work and evidence

1. Preserve worktree/runtime/model/corpus identities; reproduce frozen worker and
   inspect raw SDK output and decode windows before modifying production files.
2. Freeze independent medium, continuous boundary, intentional silence and mixed
   fixtures before decoding. Keep original short, English, Mandarin, mixed,
   pauses/noise and actual video. Fixed accuracy and coverage/omission gates.
3. Measure all four profiles (preprocessing, model/total wall, RTF, invocations,
   RSS and macOS footprint). Classify every nonfinite path; strict authoritative
   JSON must fail closed. Never turn diagnostic omission into authority success.
4. Only select a profile if every required authority/accuracy/medium/short gate
   passes. Implement smallest profile if justified; otherwise keep FAILED.
   Any implementation/adapter change invalidates tuple, never edits old receipt.
5. Run adversarial, Phase9/8/7/integrated/full backend, frontend/static/browser,
   DB and preserved-tree checks; actual complete E2E and medium no-model restore
   if a profile is qualified. Record unsupported cases honestly.
6. Three self reviews: root cause, qualification, product. Fix material defects,
   retest, scoped commits, exact requested final report and verdict.

Reuse DIRECT: existing runtime/model, Python wave/json, numpy, ffmpeg/macOS say,
existing scorers and job/persistence/qualification/Backup validators. No new
runtime or neural VAD. DESIGN.md is retained as the unchanged UI reference.
Historical Phase9 receipt and diagnostic evidence remain untouched.
