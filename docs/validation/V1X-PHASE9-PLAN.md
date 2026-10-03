# Phase 9 execution plan

Owner authorization: continuous sole-executor Phase 9 task. Exact baseline
`5324ebb3c38e941168bd9de156550bbbb65573ff`; schema 32. Work only on
`chatgpt/v1x-acoustic-qualification`. No merge, push, alternate models or dependency
upgrades. The owner's task supersedes historical multi-role handoff requirements.

1. Verify baseline and snapshot all protected worktrees. Reproduce the pinned
   environment from the existing lock entirely offline. Run Phase 8 focused tests.
2. Use the installed Hugging Face library to resolve only
   `mlx-community/whisper-large-v3-turbo`, fetch required config/weights at that
   exact commit, and seal regular files with SHA-256 and Phase 8 model identity.
3. Freeze ground truth before execution. Generate bounded nonpersonal English,
   Mandarin, mixed, short, normal, medium, silence and noisy speech locally with
   installed OS voices and media tools under network denial. Retain generation
   specification and hashes, not bulky binaries.
4. Measure actual sandboxed MLX execution with the fixed Phase 8 decoding profile.
   Score deterministic English WER, Mandarin CER and mixed Han-character/Latin-token
   errors. Enforce per-clean-sample gates of 15%, 15%, 20%; detect known speech
   omission separately. Preserve all failures and actual unedited output.
5. Add minimal machine qualification receipt/state diagnostics outside portable
   DATA and SQLite. Bind the complete tuple and immutable corpus/results. Model
   selection cannot create PASS. Test material-change invalidation and tampering.
6. Exercise real Local audio/video jobs, persisted transcript, process restart,
   normal Summary and durable timed Evidence. Isolate model absence afterward;
   prove trusted authority survives. Verify offline operation and backup exclusion.
7. Add adversarial tests and localized diagnostics without new navigation. Run
   Phase 9, Phase 8, Phase 7, integrated and full backend/frontend/static/database
   validation plus browser language/viewport matrices. Fix in-scope defects.
8. Review the complete baseline-to-final diff afresh, verify protected worktrees
   and dependency/migration identities, record truthful qualification PASS/FAIL,
   and make scoped local commits. Final report maps every completion criterion.

Reuse: DIRECT existing mlx-whisper 0.4.3, MLX, Hugging Face download library,
macOS say, ffprobe/ffmpeg, pytest/frontend tools; ADAPT existing offline executor,
private machine capability storage and localized Local diagnostics; DIRECT existing
immutable snapshot/trusted transcript/Summary/Evidence/Backup contracts. No new
runtime, production dependency, architecture or schema migration.

Synthetic speech proves this bounded private-stage profile only. It cannot support
population-level human speech accuracy or public distribution certification.
