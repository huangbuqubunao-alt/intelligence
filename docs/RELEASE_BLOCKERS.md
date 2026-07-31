# Release Blockers — Items Requiring Human Decision

- Status: `BLOCKED`
- Last updated: 2026-07-31
- These items cannot be resolved by code changes alone. Each requires
  explicit authorization, legal review, or production credential access
  from the designated decision maker.

## 1. Supply Chain & License Decisions

### 1.1 mutagen GPL-2.0-or-later Distribution

- **Decision maker**: PO + TL
- **Risk**: `yt-dlp[default]` transitively depends on `mutagen==1.48.1`
  (GPL-2.0-or-later). Distributing the package as a binary or bundled
  dependency may trigger GPL copyleft obligations.
- **Required input**: Legal review of distribution model (source-only
  pip install vs. binary wheel vs. standalone executable).
- **Pass criteria**: Written decision on distribution form; if binary,
  GPL compliance plan including source availability.

### 1.2 o200k_base.tiktoken File-Level License

- **Decision maker**: PO + TL
- **Risk**: The `o200k_base.tiktoken` resource is pinned at SHA-256
  `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`.
  Its origin, license, copyright holder, and NOTICE requirements are
  undocumented.
- **Required input**: Source attribution, license identification,
  NOTICE/credit text for distribution.
- **Pass criteria**: Written license conclusion; NOTICE text added to
  `docs/THIRD_PARTY_NOTICES.md` if required.

### 1.3 OpenAI SDK / tiktoken / Jinja2 / MarkupSafe NOTICE Evidence

- **Decision maker**: TL
- **Risk**: Apache-2.0 (OpenAI SDK), MIT (tiktoken), BSD-3-Clause
  (Jinja2, MarkupSafe) all require NOTICE preservation in distribution.
- **Required input**: Complete transitive dependency list with licenses
  and NOTICE texts for the final distribution artifact.
- **Pass criteria**: SBOM covers all direct and transitive dependencies;
  NOTICE texts verified and included.

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
