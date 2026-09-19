# V1_LOCAL_VALIDATION_HANDOFF.md

Status: CURRENT — 2026-09-20  
Purpose: minimize duplicate local/Codex work by validating only the active Draft stack, in dependency order, with exact target heads.

## 1. Local repository truth

Authoritative local starting worktree:

`/Users/hua/Documents/yia-worktrees/v1-product-ux-repair`

Expected remotes after the repository migration:

- `origin` → legacy private repo `huangbuqubunao-alt/youtube-intel`
- `github` → current private repo `huangbuqubunao-alt/intelligence`

Do **not** rewrite either remote merely to make validation proceed.

Before every validation session:

```bash
cd /Users/hua/Documents/yia-worktrees/v1-product-ux-repair
pwd
git rev-parse --show-toplevel
git status --short --branch
git branch --show-current
git rev-parse HEAD
git remote -v
```

Hard stop if the tracked worktree is dirty.

For a target Draft, fetch from **github**, verify the exact head, then create a detached temporary worktree:

```bash
git fetch github <target-branch>
git rev-parse FETCH_HEAD
git worktree add --detach /tmp/<validation-name> <exact-head-sha>
cd /tmp/<validation-name>
git rev-parse HEAD
git status --short --branch
```

Never validate a current Intelligence PR by fetching `origin`.

## 2. Executor ownership

### EvoX first

Use EvoX for sandbox-compatible work:

- pytest/unit/integration tests
- frontend typecheck
- frontend Vitest
- frontend production build
- Ruff
- mypy
- `git diff --check`
- non-host migration/schema checks

Known EvoX blockers are not code failures:

- localhost bind / browser E2E requiring local server
- user proxy access
- real YouTube/yt-dlp through local proxy
- Ollama / Whisper / host local services
- known Vitest/Tinypool teardown-only runner failures

Classify failures before changing code.

### Codex escalation only

Use Codex for:

- localhost/browser acceptance
- real YouTube/proxy
- Ollama/local-model qualification
- app restart / host persistence
- real Backup/Restore drill
- ambiguous authority/migration failures after reproducible EvoX evidence
- final high-risk migration/authority review

Do not rerun green EvoX checks in Codex without a specific reason.

## 3. Group A — M4/M5 authority stack

Validate in order:

### A1. PR #24 — M4C Evidence excerpt / stance

Branch: `chatgpt/m4c-evidence-excerpt-stance`  
Head: `63bbc71a02130462142b5d3d7f2ee2b0e520d0d8`  
Base: PR #19 / `810bd245136f9994ee1dac97c16fa21b2be9b2da`

Focused checks:

```bash
python -m pytest tests/integration/test_state_store.py -q
python -m pytest tests/integration/test_task022_personalized_distillation.py -q
python -m pytest tests/unit/test_local_api.py -q
cd frontend
npm run typecheck
npm test
npm run build
cd ..
python -m ruff check src/youtube_intel tests
python -m mypy src/youtube_intel
git diff --check
git status --short
```

Acceptance focus:

- migration 017
- legacy NULL stance remains readable
- mixed legacy/new stance fails closed
- only supporting / contradicting / conditional are semantic stances
- at least one supporting Evidence required for admitted Intelligence
- generic caller text cannot become trusted `source_excerpt`
- original excerpt absence is shown honestly
- translation absence is shown honestly
- legacy `DependencyRelation.EVIDENCE_SUPPORT` is never interpreted as semantic supporting stance
- contradicting/conditional display comes from revision↔Evidence stance authority

Known remaining product boundary: trusted runtime excerpt capture is still incomplete. A green PR #24 does not by itself prove real source excerpts are captured in production.

### A2. PR #27 — M5A validation posture

Branch: `chatgpt/m5a-validation-posture-on-m4c-v2`  
Head: `ce48d3d08e3610558fe57dff94ccab2aaebebc60`  
Base: PR #24

Do **not** rerun A1 backend tests if A1 is green.

Focused delta:

```bash
cd frontend
npm run typecheck
npm test
npm run build
cd ..
git diff --check
git status --short
```

Acceptance focus:

- NEW / PENDING_CONFIRMATION / CONFIRMED / DISPUTED / UPDATED copy remains finite
- no numeric confidence percentage
- validation posture is not presented as a confidence score

### A3. PR #32 — M5B durable no-new Intelligence success

Branch: `chatgpt/m5b-no-new-intelligence-result`  
Head: `411be176373f35de3c77544613229f91c6703130`  
Base: PR #27

Focused backend:

```bash
python -m pytest tests/integration/test_state_store.py -q
python -m pytest tests/integration/test_task022_personalized_distillation.py -q
python -m pytest tests/unit/test_local_api.py -q
python -m ruff check src/youtube_intel tests
python -m mypy src/youtube_intel
git diff --check
```

Focused frontend:

```bash
cd frontend
npm run typecheck
npm test
npm run build
cd ..
git status --short
```

Acceptance focus:

- schema reaches migration 018
- `SUCCEEDED` admitted-Intelligence path remains unchanged
- `SUCCEEDED_NO_NEW_INTELLIGENCE` is a positive terminal result
- no Intelligence/revision/card is created for positive zero
- zero result is never inferred from an empty Intelligence list
- exact current canonical Evidence set required
- zero-result sidecar and protected checkpoint become immutable
- restart reads back the same effective zero result
- repeat execution does not dispatch a second transport call
- read-time Evidence-set hash revalidation fails closed on tamper
- API distinguishes NOT_PROCESSED / SUCCEEDED / SUCCEEDED_NO_NEW_INTELLIGENCE
- UI contains no confidence percentage or sufficiency score

Do **not** claim full Source Run positive-zero acceptance from A3. Migration 012 still has raw-SUCCEEDED completion triggers; that is a separate authority follow-up.

## 4. Group B — M10 Backup / Restore

### B1. PR #28 — truthful readiness surface

Branch: `chatgpt/m10a-backup-status-on-current-v2`  
Head: `b9985a34811aa00decb5fcb8711d440f87bc896a`  
Base: PR #27

Focused delta:

```bash
python -m pytest tests/unit/test_local_api.py -q
cd frontend
npm run typecheck
npm test
npm run build
cd ..
git diff --check
```

Host-only E2E, when available:

```bash
cd frontend
npm run test:e2e
```

Acceptance focus: no backup/restore action is shown before a production service exists; temporary drills are not presented as real backups.

### B2. PR #29 — core archive + restore staging

Branch: `chatgpt/m10b-core-backup-on-hardened-stack`  
Head: `22e74544b9131322dfbb00f8bffee11b13d6ac57`  
Base: PR #28

Current-branch validation:

```bash
python -m pytest tests/integration/test_core_backup.py -q
python -m ruff check src/youtube_intel/core_backup.py src/youtube_intel/runtime.py tests/integration/test_core_backup.py
python -m mypy src/youtube_intel
git diff --check
```

Important: #29 is currently a **pre-M5B schema-line** Draft. Passing these commands validates #29 only on its own branch. It does not prove compatibility with PR #32 / schema v18.

Before integrated M10 validation after M5B, reconcile:

- `CURRENT_SCHEMA_VERSION = 18`
- backup/restore manifest schema checks against v18
- `distillation_no_new_intelligence_results` preservation
- backup quiescence must not classify a validated M5B positive-zero result as permanently active merely because its legacy raw checkpoint remains PENDING
- restore staging must revalidate the full v18 database before any live replacement

Real data Backup/Restore drill remains Codex/host-only and is required before M10 acceptance.

## 5. Group C — Following / Topic UX

### C1. PR #30 — progressive Following setup

Branch: `chatgpt/m2c-following-progressive-on-current`  
Head: `c3c08f1f795b58acadbe24f48b10a80d841739d4`  
Base: PR #28

```bash
cd frontend
npm run typecheck
npm test
npm run build
cd ..
git diff --check
```

Host-only:

```bash
cd frontend
npm run test:e2e
```

Acceptance focus:

- normal first-run path shows URL + monitoring and recommended defaults
- advanced controls are hidden, not deleted
- recommended copy visibly discloses daily schedule/default behavior before submit
- edit mode still exposes full existing controls
- only existing Source/policy/schedule commands are used

### C2. PR #31 — Topic rename

Branch: `chatgpt/m7a-topic-rename-on-current`  
Head: `1ef73cfb91768bb378d6e38876f83e0a6ca6af53`  
Base: PR #30

Do not rerun C1 if C1 is green.

```bash
cd frontend
npm run typecheck
npm test
npm run build
cd ..
git diff --check
```

Acceptance focus:

- label-only rename
- persisted PATCH command
- failure keeps edit form open and surfaces the error
- no Intelligence/Evidence/membership/lifecycle rewrite
- no archive/merge/split/lifecycle automation

## 6. Result classification

Every validation report must end with exactly one:

- `VALIDATION_PASS`
- `CODE_FAILURE_FOUND`
- `ENVIRONMENT_BLOCKED`
- `RUNNER_TOOLING_FAILURE_ONLY`
- `TARGET_OR_REPOSITORY_MISMATCH`

For every credited PASS record:

- repository
- branch
- exact HEAD
- command
- exit code
- passed/failed count where available
- executor
- environment blocker, if any

Interrupted runs without exact completed-command evidence are not credited.

## 7. Stop rules

Stop and ask the Owner before:

- destructive migration or restore behavior
- changing Evidence authority boundaries
- inventing a new stance/confidence/sufficiency axis
- weakening provider/credential/side-effect guards
- silently enabling cloud or paid calls
- changing Source Run authority to fake an Intelligence admission
- public distribution

Do not use local validation pressure as a reason to weaken trusted authority.
