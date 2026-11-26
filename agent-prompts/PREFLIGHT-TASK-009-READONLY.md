# TASK-009 read-only preflight — Obsidian note and safe filesystem contracts

Role: Read-only Scout. Work only in `/Users/developer/Documents/youtubek agent`.

This packet authorizes inspection only. Do not modify or create any repository, temporary
Vault or temporary file, stage/commit, create a branch/worktree, run uv/tests/builds or
Python imports, install packages, access the network, read a real Obsidian Vault, inspect
credentials, or change task status.

## Authorization and baseline

At start, resolve:

```bash
git log -1 --format=%H -- agent-prompts/PREFLIGHT-TASK-009-READONLY.md
```

It must equal current clean main HEAD. Confirm TASK-003 and TASK-007 are `DONE`, while
TASK-009 is `BLOCKED/UNASSIGNED`. If main changes or becomes dirty during the Scout, stop
and report it; do not clean or wait on a writer.

Read fully in repository order: `AGENTS.md`, `docs/COLLABORATION.md`,
`docs/PROJECT_STATUS.md`, `docs/PRD.md`, `docs/SYSTEM_DESIGN.md`,
`docs/REUSE_REGISTER.md`, `docs/PRODUCT_DECISIONS.md`,
`docs/decisions/ADR-002-config-domain-contracts.md`,
`docs/decisions/ADR-003-sqlite-state-store-contract.md`,
`tasks/TASK-009-obsidian-notes.md`, and this packet. Inspect current source/tests/config/
lockfile statically. The repository is not CodeGraph-indexed; do not create an index.

## Questions to close

Produce evidence, not an implementation:

1. **Public contracts** — inventory exact `KnowledgeSink`, `NoteRef`, `NoteKind`,
   `VideoMetadata`, transcript, score, optional `AnalysisResult`, Artifact kinds,
   Provider-call/Job/Pipeline states and `complete_stage` surface. Identify any shared
   contract gap without inventing a competing object.
2. **Write eligibility** — freeze behavior for low-value videos, high-value videos with
   analysis, high-value videos with `analysis=None` because cloud was disabled/skipped,
   already-complete notes, title changes and explicit reruns. TASK-009 must not own cloud
   calls or orchestration.
3. **Stable identity and path** — define deterministic safe filename
   `<safe-title>--<video_id>.md`, title normalization/truncation, Unicode/reserved names,
   collision behavior, stable rename/update policy and `NoteRef.relative_path`. Confirm
   every path is relative to the configured Vault subdir and never exposes an absolute
   Vault path.
4. **Vault boundary** — map config-time and every-write checks for absolute
   `vault_root`, relative `vault_subdir`, `..`, absolute child paths, intermediate/final
   symlinks, directory replacement races, non-directory parents and permission failures.
   Define how the Adapter fails closed without touching unrelated notes.
5. **Managed and user regions** — freeze exact markers/grammar for the system-managed body
   and `我的思考`; behavior for first create, unchanged upsert, user edits, missing,
   duplicated, nested or malformed markers, legacy/unmanaged file and invalid UTF-8.
   Preservation must be byte-for-byte for the user region.
6. **Frontmatter and Markdown** — enumerate required keys, stable ordering/types, quoting,
   YAML-safety, timestamp/timezone forms, topic/tag/link encoding, untrusted title/content
   escaping and the body sections for `analysis` present vs absent. Model text must not be
   able to terminate frontmatter or management markers.
7. **Template reuse** — compare approved Jinja2 reuse with standard-library/manual
   rendering. Recommend `DIRECT/ADAPT/REFERENCE/REJECT`, but do not guess an offline-
   unverifiable version. Specify strict undefined behavior, autoescape/filters,
   sandbox/loader boundary and whether Jinja2 is truly necessary. Re-evaluate the
   registered `yt2md` sources as reference only; no code copying or direct Vault access.
8. **Atomicity and recovery** — define same-directory temporary write, permission mode,
   flush/fsync/atomic replace/directory sync, cleanup after failure, pre/post hash checks,
   Artifact write, `ANALYSIS_READY -> NOTE_WRITTEN`, Job completion, rollback/requeue and
   crash windows using existing Repository methods. Determine whether TASK-009 can avoid
   Schema/migration or `state.py` changes.
9. **Scope and tests** — propose the smallest vertical file/test split, including fixtures
   or templates and handoff. Cover temporary-Vault-only creation/upsert, no-op hash,
   title/collision, path/symlink race, malformed existing note, injected write failures,
   user-region preservation, YAML parse/types, optional analysis and real SQLite stage
   completion. If scope exceeds a focused M slice or shared changes are needed, propose a
   prerequisite TASK-009A.
10. **Approvals** — separate what is already approved from what still needs approval:
    Jinja2/version/lock/download, template/file scope, temporary file operations, real
    Vault access, real user note content, deletion/rename behavior, and validation
    commands. Real Vault access must remain unapproved.

## Required response

Return only a concise structured report:

```text
Preflight: TASK-009
Role: Read-only Scout
Observed main commit:
Repository changes: None
Spec/contract consistency: PASS | DECISION NEEDED
Existing contract/repository inventory:
Eligibility/output matrix:
Filename/path/Vault boundary recommendation:
Managed-user-region recommendation:
Frontmatter/template/reuse recommendation:
Atomicity/transaction/recovery recommendation:
Suggested task split and exact file groups:
Offline test matrix:
Already approved:
Approvals still needed:
Risks/blockers:
Proposed decisions N-01...:
Recommended next action:
```

Do not claim a dependency version was verified unless present in the repository. Do not
write a handoff or commit. End by confirming `git status --short` has no changes.
