# Release Blockers — Items Requiring Human Decision

- Status: `BLOCKED FOR PUBLIC DISTRIBUTION`
- Last updated: 2026-08-31 (current controlled target SBOM/NOTICE reconciliation)
- P1 remediation status: The three Codex Maintainer Review P1 blockers
  (security scanner fail-open, backup/recovery drill false-pass, Obsidian
  Markdown/HTML rendering safety) are remediated on `workbuddy/fix-rc-p1`.
- Remaining items below cannot be resolved by code changes alone. Each
  requires explicit authorization, legal review, or production credential
  access from the designated decision maker.

## Current final-review additions

- TASK-014B9 is `QUALIFIED / CLOSED` and TASK-014B11 is `INTEGRATED / CLOSED` on
  `main@21bf38f`; neither closure is a public-distribution approval.
- TASK-016 has no qualified live Deep Analysis provider and no Product Owner
  acceptance of real qualified-provider output. TASK-016G remains unauthorized.
- The canonical security scanner is fail-closed and currently exits non-zero on
  11 documented TASK-016 test fixtures. No new release-candidate finding exists,
  but no formal release-policy closure treats a non-zero global scan as green.

## 0. Project License (NEW — Added after RC Reviewer feedback)

### 0.1 Project Own License / Owner Identity Is Partially Resolved

- **Decision maker**: PO + TL (codebase owner)
- **Current state**: PO/TL selected `PRIVATE / PROPRIETARY / LIMITED-DISTRIBUTION`.
  Root `NOTICE` and `pyproject.toml` `license.file=NOTICE` encode that restrictive
  posture without inventing a legal owner identity. It does not permit public
  distribution.
- **Risk**: The selected notice is intentionally restrictive and cannot support a
  broader release until its legal owner is recorded. Target-artifact third-party
  obligations and GPL-sensitive future bundled modes remain separate concerns.
- **Remaining input**: PO/legal records the copyright-holder identity before
  broader external distribution. Any future attempt to ship the BPE file needs
  its separate file-level rights conclusion; ADR-028 currently excludes it.
  Any future bundled mode must also satisfy §1.1 mutagen constraints.
- **Decision package**: The technical artifact inventory and the selected
  limited-distribution posture are recorded in
  `docs/LICENSE_DISTRIBUTION_DECISION_PACKAGE.md`.
- **Pass criteria**: Legal owner identity recorded; target-specific SBOM/NOTICE
  complete; proprietary notice and package
  metadata remain consistent in the built artifact.
- **Blocker level**: DISTRIBUTION BLOCKER — no public release until resolved.

## 1. Supply Chain & License Decisions

### 1.1 mutagen GPL-2.0-or-later Distribution

- **Current controlled target: RESOLVED.** The boundary is frozen as first-party
  source/wheel/sdist with separately package-manager-resolved dependencies. The
  fresh offline archives contain no `mutagen`, dependency wheel, `site-packages`,
  GPL, or `COPYING` payload. `mutagen==1.48.1` remains a separately installed
  `yt-dlp[default]` transitive runtime dependency and is accurately listed as
  GPL-2.0-or-later in SBOM-B/NOTICE Set B.
- **Future physical-distribution gate: BLOCKED.** An application bundle,
  materialized venv, container, installer, or copied dependency set is not
  authorized. Before any such form, PO/TL/legal must complete a target-specific
  GPL-sensitive compliance package covering included components, license texts,
  attribution, and source/source-offer obligations where applicable.
- **No legal approval is implied.** This technical resolution neither characterizes
  GPL effects beyond the documented facts nor authorizes public distribution.

### 1.2 o200k_base.tiktoken File-Level License — Mitigated for Current Artifact

- **Current state**: The `o200k_base.tiktoken` resource is pinned at SHA-256
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`.
  `O200K_BASE_REDISTRIBUTION_EVIDENCE.md` verifies the canonical Blob identity
  and classifies first-party evidence as `C`: OpenAI distributes the file, but
  no evidence expressly licenses downstream redistribution or supplies its
  file-level NOTICE/credit requirement.
- **Disposition**: ADR-028 removes the file from project source/wheel/sdist
  artifacts and admits only an explicitly user/admin-provisioned local copy.
  Runtime remains local, fixed-hash and fail-closed, with no download or
  tokenizer fallback. Therefore no project redistribution of this Blob occurs
  in the current controlled artifact.
- **Status**: `RESOLVED FOR CURRENT CONTROLLED ARTIFACT`; classification C and
  the lack of a downstream grant remain preserved. Any future shipped copy
  reopens this item and requires rightsholder/legal confirmation of its license
  and NOTICE/credit text.

### 1.3 Target-runtime inventory / NOTICE evidence

- **Current controlled target: RESOLVED.** SBOM-A distinguishes physical project
  artifact content from SBOM-B's 74 separately installed macOS-arm64 runtime
  packages (9 direct, 65 transitive), with metadata/license evidence and explicit
  dev exclusion. NOTICE A/B/C freezes the same physical-versus-runtime boundary.
- **Future gate:** a target that copies dependencies must collect and present all
  applicable license/notice material for its actual contents; it cannot reuse
  this source/wheel/sdist conclusion.

### 1.4 MLX Whisper / ffmpeg / Ollama Model Licensing

- **Decision maker**: PO + TL
- **Risk**: If local models are included in distribution: `mlx-whisper`,
  model weights, ffmpeg (GPL), and Ollama model licenses each require
  separate review.
- **Required input**: Decision on whether to bundle or require separate
  installation; if bundled, license compatibility analysis.
- **Pass criteria**: Written exclusion or inclusion decision with
  license compliance plan for each component.

## 2. Security & Privacy Sign-Offs

### 2.1 Cloud SDK Isolation Verification

- **Decision maker**: Security Reviewer
- **Risk**: The isolated child process (`cloud_llm.py`) must not import
  the SDK in the main process, must use a whitelist environment, and
  must receive credentials only through anonymous pipes.
- **Required input**: Review of ADR-008 implementation against the
  isolation requirements.
- **Pass criteria**: Security Reviewer confirms: no main-process SDK
  import, whitelist env, pipe-only credential passing, no credential
  leakage through env/argv/files/logs/exceptions.

### 2.2 Vault & Template Distribution Boundary

- **Decision maker**: Privacy Reviewer
- **Risk**: Managed Obsidian notes must not include real user content in
  distribution artifacts. Templates must be safe defaults.
- **Required input**: Review that no real Vault content, user notes, or
  user templates are included in any distribution artifact.
- **Pass criteria**: Privacy Reviewer confirms clean artifact content.

### 2.3 At-Most-Once Risk Acceptance

- **Decision maker**: PO
- **Risk**: Three residual crash windows exist where recovery is
  best-effort, not exactly-once:
  1. Provider success → SQLite commit
  2. File atomic replace → SQLite commit
  3. Audio cleanup final CAS
- **Required input**: PO explicitly accepts the at-most-once semantics
  and documents the accepted risk.
- **Pass criteria**: PO signature on the risk disclosure.

## 3. Operational Authorization

### 3.1 Backup & Recovery Drill (Real Environment)

- **Status**: Automated drill v3 remediated and passing on `workbuddy/fix-rc-p1`.
- **Decision maker**: QA + TL
- **Risk**: The automated drill (`scripts/backup_recovery_drill.sh`)
  validates temporary environments. A real drill requires temporary
  SQLite/DATA/Vault with real pipeline data.
- **Required input**: Authorization to run the drill in a controlled
  temporary environment and record results.
- **Pass criteria**: Drill commands, versions, schema, results, and
  failure disposition documented.

### 3.2 Four-Phase Real Smoke Authorization

- **Decision maker**: PO (per phase)
- **Risk**: Real YouTube/smoke requires network access, and potentially
  media/ffmpeg/Whisper/Ollama/OpenAI. Each phase has separate
  authorization requirements per `SMOKE_AUTHORIZATION_MATRIX.md`.
- **Required input**: Phase-by-phase PO approval with video IDs,
  resource limits, and data retention plans.
- **Pass criteria**: All four phases executed and documented per the
  authorization matrix.

### 3.3 Real Vault & Launchd Authorization

- **Decision maker**: PO
- **Risk**: Writing to real Obsidian Vault or registering launchd
  services affects user data and system configuration.
- **Required input**: Explicit PO approval for each.
- **Pass criteria**: Written authorization with scope and rollback plan.

## 4. Final Sign-Offs

### 4.1 PO / TL / QA / Privacy Reviewer Signatures

- **Decision maker**: All four roles
- **Required input**: Review of this document, `RELEASE_CHECKLIST.md`,
  and all evidence links.
- **Pass criteria**: All four roles sign `GO` in
  `docs/RELEASE_CHECKLIST.md` final signature table.

## 5. Non-Blocking Known Risks

These are documented but do not block the RC:

1. **Recovery semantics**: At-most-once best effort, not exactly-once.
   Documented in README and PROJECT_STATUS.
2. **YouTube subtitle compatibility**: Real smoke tests showed
   `INVALID_RESPONSE` for specific video IDs. B6-B11 diagnostic chain
   provides safe classification without exposing content.
3. **Apple Silicon specificity**: MLX Whisper and model dependencies
   are Apple Silicon specific. Non-Apple platforms are not supported
   for local transcription/scoring.
4. **Single-operator scope**: The tool is designed for a single
   operator. Multi-user or shared access is out of scope for V1.
