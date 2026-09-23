# Release Blockers — Items Requiring Human Decision

- Status: `BLOCKED FOR PUBLIC DISTRIBUTION`
- Last updated: 2026-08-31 (current controlled target SBOM/NOTICE reconciliation)
- P1 remediation status: The three Codex Maintainer Review P1 blockers
  (security scanner fail-open, backup/recovery drill false-pass, Obsidian
  Markdown/HTML rendering safety) are remediated on `workbuddy/fix-rc-p1`.
- Remaining items below cannot be resolved by code changes alone. Each
  requires explicit authorization, legal review, or production credential
  access from the designated decision maker.
- **Current governance policy (PO decision after `026e9b8` audit):** for the
  current personal/private/proprietary controlled source/wheel/sdist posture,
  named independent Security/Privacy Reviewer, separate TL, separate QA, and
  the multi-role signature table are conditional future controls, not current
  blockers. This preserves technical evidence requirements and every explicit
  PO decision/authorization gate. Re-evaluate applicable roles at public or
  broader distribution, commercial/customer/contractual use, bundle/container/
  installer/app-store, legal-identity/ownership, multi-developer, or externally
  imposed compliance trigger.

## Current final-review additions

- TASK-014B9 is `QUALIFIED / CLOSED` and TASK-014B11 is `INTEGRATED / CLOSED` on
  `main@21bf38f`; neither closure is a public-distribution approval.
- TASK-016 has no qualified live Deep Analysis provider and no Product Owner
  acceptance of real qualified-provider output. TASK-016G remains unauthorized.
- The canonical security scanner is fail-closed and currently exits non-zero on
  exactly 11 documented TASK-016 intentional-positive test fixtures. No new
  release-candidate finding exists. The Product Owner / Tech Lead accepted a
  finite release-policy exception for this exact matrix at `main@5e15d62`, for
  the current controlled private source/wheel/sdist posture only. The scanner
  remains exit `1`; it is not globally clean or PASS. The finding-by-finding
  evidence, conditions, and re-review triggers are in
  [SECURITY_SCANNER_FIXTURE_DISPOSITION.md](SECURITY_SCANNER_FIXTURE_DISPOSITION.md):
  all 11 are intentional positive test fixtures, are absent from fresh wheel/
  sdist archives, and have no production-runtime reachability. The controlled
  Git source tree does contain the tracked test corpus. **The security technical
  release blocker is resolved for the current controlled release.** No broader
  distribution, scanner weakening, allowlist, or suppression is approved.
- This does not close provider, retained PO-authorization, legal/distribution,
  or operations blockers. Named organizational reviewer and final-table controls
  are deferred only for the current posture under the PO policy above. The
  ADR-008 technical isolation review is recorded separately in §2.1. The
  non-blocking future follow-up is a first-class
  fail-closed scanner scope/intentional-fixture disposition design; it covers no
  future finding automatically.

## 0. Project License (NEW — Added after RC Reviewer feedback)

### 0.1 Project Own License / Owner Attribution Is Resolved for Current Controlled Artifact

- **Decision maker**: PO + TL (codebase owner)
- **Current state**: PO/TL selected `PRIVATE / PROPRIETARY / LIMITED-DISTRIBUTION`.
  Root `NOTICE` and `pyproject.toml` `license.file=NOTICE` encode that restrictive
  posture and record `墨竹` as the current pseudonymous first-party owner/
  copyright attribution identifier. This does not permit public distribution.
- **Current controlled-artifact disposition: RESOLVED.** The attribution is not
  represented as a verified legal name, legal entity, trademark, copyright
  registration, or IP-assignment proof. No unnecessary PII is recorded.
- **Future verified-identity gate:** before a broader external distribution or
  any action whose governing policy requires verified legal identity, PO/legal
  must establish the needed controlled legal record separately. Any future
  attempt to ship the BPE file needs its separate file-level rights conclusion;
  ADR-028 currently excludes it. Any future bundled mode must also satisfy §1.1
  mutagen constraints.
- **Decision package**: The technical artifact inventory and the selected
  limited-distribution posture are recorded in
  `docs/LICENSE_DISTRIBUTION_DECISION_PACKAGE.md`.
- **Pass criteria for current controlled artifact**: Pseudonymous first-party
  attribution recorded; target-specific SBOM/NOTICE complete; proprietary notice
  and package metadata consistent in the built artifact.
- **Blocker level**: Current controlled-artifact owner-attribution blocker
  resolved. A future verified-identity requirement remains a distribution/legal
  gate only when the governing action requires it; no public release is approved.

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

## 2. Security & Privacy Technical Reviews and Conditional Human Review

### 2.1 Cloud SDK Isolation Verification

- **Current requirement**: ADR-008 technical review evidence is required.
  A named independent Security Reviewer is deferred / not required for the
  current posture.
- **Risk**: The isolated child process (`cloud_llm.py`) must not import
  the SDK in the main process, must use a whitelist environment, and
  must receive credentials only through anonymous pipes.
- **Required input / pass criteria**: Evidence confirms no main-process SDK
  import, whitelist env, pipe-only credential passing, and no credential
  leakage through env/argv/files/logs/exceptions.
- **Technical evidence disposition (2026-08-31): RESOLVED.**
  [ADR-008 cloud-SDK isolation security review](ADR008_CLOUD_SDK_ISOLATION_SECURITY_REVIEW.md)
  traces the current OpenAI and Moonshot-compatible paths, confirms the
  no-main-process-import and literal child-environment boundary, and records
  offline socket-deny/fake-transport/credential/BPE evidence. Technical P0: `0`;
  release-critical technical P1: `0`.
- **Conditional human-review boundary:** a named independent Security Reviewer
  is not required for the current posture. It must be re-evaluated when a
  relevant public/broader-distribution, commercial/customer/contractual,
  multi-developer, material cloud/credential-boundary, or externally imposed
  compliance trigger occurs. No legal approval, provider qualification, or
  release is implied.

### 2.2 Vault & Template Distribution Boundary

- **Current requirement**: Vault/template technical review evidence is required.
  A named independent Privacy Reviewer is deferred / not required for the
  current posture.
- **Risk**: Managed Obsidian notes must not include real user content in
  distribution artifacts. Templates must be safe defaults.
- **Required input / pass criteria**: Evidence confirms no real Vault content,
  user notes, or user templates are included in any distribution artifact.
- **Technical evidence disposition (2026-08-31): RESOLVED.** The
  [Vault/template privacy review](VAULT_TEMPLATE_PRIVACY_REVIEW.md) traces the
  runtime-only Vault boundary, fixed package templates, rendered-output
  destination, credential/log/cache/provenance controls, and fresh offline
  archive contents. Wheel and sdist contain neither Vault/runtime output nor
  the synthetic privacy sentinels; technical P0: `0`, release-critical
  technical P1: `0`.
- **Conditional human-review boundary:** a named independent Privacy Reviewer
  is not required for the current posture. Re-evaluate at relevant public/
  broader-distribution, commercial/customer/contractual, multi-developer,
  material Vault/template/build-boundary, or externally imposed compliance
  trigger. Historical controlled-Git governance metadata remains a
  non-release-critical P2 source-hygiene re-review trigger before broader/public
  source distribution, not Vault content or wheel/sdist payload.

### 2.3 At-Most-Once Risk Acceptance

- **Decision maker**: PO
- **PO decision record**:
  1. **Provider success → SQLite commit:** `REJECT / REQUIRE REMEDIATION`.
     Remediation is complete: durable dispatch state now fails closed on an
     expired `INTENT`/`RESULT_UNKNOWN` call, never auto-redispatches it, and
     never lets cache/artifact evidence convert it to trusted success. The
     residual is an operator-visible terminal incomplete item, not exactly-once
     semantics. A future live-provider qualification remains separately
     authorized and must validate its selected provider contract.
  2. **File atomic replace → SQLite commit:** `ACCEPT` for the current
     personal/private/proprietary controlled source/wheel/sdist posture only;
     no Window-2 behavior changed.
  3. **Audio cleanup final CAS:** `ACCEPT` for the current
     personal/private/proprietary controlled posture only; no Window-3 behavior
     changed.
- **Evidence**: `AT_MOST_ONCE_RESIDUAL_RISK_PO_DECISION.md` records the finite
  decisions, Window-1 recovery protocol, migration-safe legacy handling, and
  exact residual. These decisions do not accept other crash windows, qualify a
  provider, authorize TASK-016G, operational validation, or distribution.
- **Current gate status**: **RESOLVED FOR CURRENT WINDOW-1 POLICY**. It does
  not make the release `GO`; the live-provider, real-output, and operational
  gates below remain independently blocked.

## 3. Operational Authorization

### 3.1 Backup & Recovery Drill (Real Environment)

- **Status**: Automated drill v3 remediated and passing on `workbuddy/fix-rc-p1`.
- **Current M10 disposition (2026-09-24): PASS** for the owner-authorized
  Intelligence-managed core scope on a task-owned clone of real pipeline data.
  The full round-trip, controlled restart, corrupt-archive rejection, restored
  M8 Evidence translation, and Vault exclusion are recorded in
  [`M10_BACKUP_RESTORE_ACCEPTANCE.md`](M10_BACKUP_RESTORE_ACCEPTANCE.md) and
  [Issue #10](https://github.com/huangbuqubunao-alt/intelligence/issues/10).
  This closes the M10 backup/restore gate for that scope; it does not change the
  overall public-distribution `BLOCKED` status or other release gates.
- **Decision maker**: PO for the current one-owner posture; separate QA/TL
  review is conditional on a future applicable trigger.
- **Risk**: The automated drill (`scripts/backup_recovery_drill.sh`)
  validates temporary environments. The M10 drill separately validates the
  real-data SQLite + Intelligence-owned DATA loop. Vault content is outside its
  restore guarantee. Physical power loss and arbitrary external concurrent
  writers were not simulated; see the M10 acceptance record.
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

## 4. Current Controlled-Posture Final Authorization

### 4.1 Objective Evidence plus Product Owner Authorization

- **Decision maker**: PO for any release/distribution decision; no separate
  named TL, QA, Security Reviewer, or Privacy Reviewer signature is required
  for the current posture.
- **Required input**: All non-deferred technical, operational, and product gates
  must be satisfied, and the PO must make any required release/distribution
  authorization. This document and `RELEASE_CHECKLIST.md` remain the evidence
  roll-up.
- **Pass criteria**: The current target may be considered only after those gates
  are satisfied and an explicit PO authorization required by the selected action
  is recorded. The deferred role table cannot itself turn `NO-GO` into `GO`.

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
