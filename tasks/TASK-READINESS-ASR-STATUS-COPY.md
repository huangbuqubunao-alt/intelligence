# TASK-READINESS-ASR-STATUS-COPY

Status: READY. Root scopes this ordinary UI correction under the user request to
fix misleading local-import/transcription journeys; no new sensitive persistence.
Implementer: /root/caption_resume; reviewer: /root/intel_bounded_review.
Base: 2857acc146a0320cb9daf61ee460b556bb444fcc.
Worktree: /Users/hua/Documents/yia-worktrees/readiness-asr-status-copy.
Branch: codex/task-readiness-asr-status-copy.

## Real reproduction and done criteria

On the real isolated ASR UI 5908, a PASSED/ready model has three correctly rejected
silence/noise jobs. Content list nevertheless displays the old media snapshot
TRANSCRIPTION_UNAVAILABLE as current model unavailability. Detail correctly shows
FAILED. Its TRANSCRIPT_INVALID copy claims the executor returned text/timestamps,
although these negative inputs caused zero decoder calls.
Evidence: root docs/validation/end-to-end-user-readiness/asr-invalid-input-status-before.png.

Make saved snapshot wording factual and direct users to the actual Content
transcription status; do not infer current model readiness/failure from the old
import status. Preserve actual READY/FAILED/running states. Reword invalid-result
feedback without asserting that a model ran; explain no accepted subtitles,
original file retained, and a useful clear-speech/retry next step without claiming
the exact input cause was established.

## Scope and reuse

Only frontend/src/workspace/LocalImport.tsx, LocalTranscription.tsx,
uiLanguage.tsx, their focused tests and new task/handoff. App.tsx is not permitted
unless a concrete need is reported first. No backend, enums, runtime, gates,
retry behavior, task state, Schema, dependencies, config, credentials or data.
DIRECT existing copy functions, localization and shared Content detail. Reuse
frontend/src/workspace/DESIGN.md tokens/interaction reference; no redesign.

TDD targeted labels in Chinese/English; verify unavailable model still has its
actual setup guidance and failed/ready/running states retain accurate feedback;
no automatic submission or retries. Keep all existing assertions with the new
intentional wording where necessary, never skip/weaken them. Full frontend,
TypeScript, production build, diff check. Commit bounded implementation and
handoff, then STOP for review; no main merge or task DONE.

Parallel: raw capture backend writer (different files), pre-output model review
in separate tree. No model generation/ASR calls in this task. Root will replay
real UI against unchanged isolated PASSED model and reject fixtures before
acceptance. Existing native Picker/APFS implementation remains unchanged.
