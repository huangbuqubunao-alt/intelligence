# TASK-READINESS-02-ASR

Assigned by root: IN_PROGRESS; isolated implementer only, base `7302f244e6326616c2b1ec72d0ad5f026d21cecb`, branch `codex/task-readiness-asr`.

Goal: remove existing medium/mixed timeline failures and silence/noise hallucination safely using the approved exact installed model and deterministic PCM segmentation, prove every frozen sample under unchanged gates. Only successful complete qualification can justify a later proposed product integration; failure remains fail closed.

Approval: user 2026-10-12 explicitly approved MODEL_REMEDIATION_PROPOSAL in parent worktree. Root additionally confirmed fixed pre-inference spectral-flatness fail-closed acoustic guard is within this experiment, not a semantic speech oracle. No post-decode trimming, per-sample tuning, reference/gate changes, cloud, dependency/model upgrades, owner/config/schema/Vault writes or production activation.

Allowed: isolated research scripts and acoustic worker/executor/qualification tuple/tests/docs only. Do not edit Distillation/UI/runtime composition. Preserve all original/independent primary and negative control inputs, old FAILED evidence and receipts. Freeze input/policy hashes before inference. Coordinate GPU with root (16 GiB machine).

Reuse: DIRECT installed mlx-whisper 0.4.3 / MLX 0.32.0 / exact large-v3-turbo a4aaeec, Python wave and installed numpy/ffmpeg; DIRECT existing strict validator/scorer and corpus. ADAPT deterministic frame partition/source time mapping. No dependency additions or SDK changes.

Required: red test, focused unit tests, compile/type/Ruff; true complete frozen matrix and controls under offline sandbox; retain every raw result. If qualified, product-path jobs and later root GUI/restore. Return scoped commit plus handoff and exact observed limitations, never DONE/main merge.
