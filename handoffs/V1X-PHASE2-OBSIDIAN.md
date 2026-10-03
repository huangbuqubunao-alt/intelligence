# V1.x Phase 2: Deep Analysis → Obsidian acceptance

Date: 2026-10-03. Sole executor; no delegated agents.
Repository: `/Users/hua/youtube-intel`.
Dedicated worktree: `/Users/hua/Documents/yia-worktrees/v1x-obsidian`.
Branch: `chatgpt/v1x-obsidian-deep-analysis`.
Start: `432f085d76824dfa51a447622aa2dba23ff8bfc8`, accepted Phase 1B.

The requested names were available. The new tree started clean at exactly the
accepted commit. Before editing, pwd, top-level, branch, HEAD, status, worktree
list, accepted-HEAD ancestry and diff whitespace checks were verified. There
was no Phase 1C/M13 merge, shared-history rewrite, push, PR or deployment.

## Delivered behavior and architecture

Content detail offers an explicit localized Publish to Obsidian action. Only
native durable Phase 1B results admitted by the existing persisted verified
read and trusted Note gate are eligible. Phase 1A stays rejected. The action
works for an existing valid result even when generation is NOT_QUALIFIED.
Read, generation, launch and restart do not publish.

SQLite stays authoritative. Publication performs no database writes; the test
compares complete SQLite dumps before and after publication. Markdown edits
are never imported or used as provenance, Evidence or later analysis input.
No qualification, routing, consent, cost or production model rules change.

The existing Obsidian sink, configuration target, kind-folder convention,
filename sanitizer, Note V2 original-Evidence resolver, fixed sandboxed Jinja
templates, v1 managed/user sections, ownership validation, no-follow anchored
directory/file handling and atomic writer are reused and extended. There is
one new kind: `deep-analysis`, projected under `Deep Analysis/`.

The DACS-1 semantic hash includes canonical Content identity, output language
and knowledge-content schema identity. Canonical Content identity is
`canonical_input.video_identity`. The historical read's `content_identity` is
a generated KnowledgeContent digest, so it is stored as provenance under
`knowledge_content_identity` instead of becoming the merge key.
`result_identity` is provenance and stale-action binding only. Reruns changing
both execution and generated-content identities update the same managed file.
Title changes and restarts retain its first path. Language and supported-schema
variants have distinct semantic identities; unsupported schemas fail closed.

JSON-quoted frontmatter records kind/product/ownership, semantic identity,
canonical Content/video id, output language, knowledge schema, result identity,
generated-content digest, authoritative timestamps, durable Evidence schema
and validation policy. Five localized product roles preserve canonical claims,
with exact durable Evidence ids beside each claim. Verified original excerpts
and timing appear separately. No candidate labels, fabricated excerpts,
Evidence translations or invented wikilinks are generated.

Republish replaces frontmatter and the generated managed region, preserving the
existing user region byte for byte. Unrelated/conflicting files, duplicate
identities, malformed markers and unsafe renamed basenames fail before writing.
Relative/absolute-looking titles, Unicode/device names and symlink escapes are
covered by real filesystem tests. First publication atomically refuses a racing
new file. Updating retains the previous inode until directory fsync, enabling
rollback on an injected post-replace failure. This retains the existing writer
guarantees; it is not a general hostile-filesystem transaction protocol.

The UI localizes no-target, ineligible, stale-result and write-error states,
plus published/updated/unchanged outcomes. Long relative paths wrap at 320px.
No navigation section is added. Existing UI patterns/styles were sufficient;
no separate design system was introduced.

External vault files are outside product Backup/Restore. A real archive test
proves exclusion, restores product authority with the note absent, then
republishes to the same path. No migration, publish audit table, dependency or
lockfile change was required. No real user vault or paid/cloud/model call was
used. See [V1X-DR-004](../docs/decisions/V1X-DR-004-deep-analysis-obsidian-publish.md).

## Owner-required adversarial coverage

All scenarios use disposable real SQLite/filesystem fixtures. Parametrization
produces 39 Phase 2 integration cases.

| # | Required case | Evidence in `test_v1x_phase2_obsidian.py` |
| --- | --- | --- |
| 1 | Phase 1A rejected | `test_phase1a_is_not_publishable` |
| 2 | Trusted Phase 1B allowed | `test_trusted_publish_is_explicit_and_preserves_claim_evidence` |
| 3 | Candidate ref rejected | `test_corrupt_authority_cannot_publish[candidate]` |
| 4 | Missing durable membership rejected | Same test `[missing_membership]` |
| 5 | Cross-Content corruption rejected | Same test `[cross_content]` |
| 6 | New execution updates same note | `test_rerun_new_result_updates_same_note_and_keeps_user_region` |
| 7 | Output languages distinct | `test_language_variants_are_distinct_and_evidence_remains_original` |
| 8 | Schema identity distinct | `test_schema_identity_separates_semantics_and_unsupported_schema_fails_closed` |
| 9 | Relative traversal title safe | `test_titles_cannot_escape_vault[../../escape]` |
| 10 | Absolute title safe | Same test, Unix and Windows variants |
| 11 | Unrelated user file survives | `test_unrelated_files_and_conflicting_ownership_are_preserved` |
| 12 | Failed atomic update preserves old note | `test_atomic_update_failure_keeps_previous_note`, four injected stages |
| 13 | No target, no alternate writes | `test_missing_vault_fails_without_writes` |
| 14 | Read-only target fails safely | `test_read_only_vault_safe_failure` |
| 15 | No candidate ids in Markdown | Trusted-publish assertion and `test_candidate_labels_in_canonical_prose_cannot_leak_into_export` |
| 16 | Durable ids present | Trusted-publish per-claim assertions |
| 17 | Claim/id association retained | Trusted-publish distinct per-claim lines |
| 18 | Language frontmatter correct | Trusted-publish and language-variant tests |
| 19 | No invented wikilinks | Title, language and `test_model_authored_wikilinks_are_neutralized_without_changing_claim_text` |
| 20 | No SQLite authority mutation | Complete dump equality in trusted-publish test |
| 21 | Restart stable identity | `test_restart_and_backup_restore_exclude_external_vault` |
| 22 | Backup/Restore excludes vault | Same test, real archive, restore and republish |

Additional cases cover root/subdirectory/kind/note symlinks, first-write races,
concurrent owner edits, stale actions, unsupported persistence/policy, malformed
markers, conflicting note kinds/ownership, duplicate identities and candidate
labels echoed in canonical prose. A future supported schema is not fabricated:
the key differs for schema variants, and today's unsupported schema is rejected.

## Review and remediation

Pass 1 inspected the implementation against Phase 1A rejection, durable ids,
merge stability, language separation, one-way authority and infrastructure
reuse. Pass 2 used actual temporary vaults and injected failures. Findings fixed:
post-replace directory-fsync rollback; no-replace first creation; standalone
marker ownership; candidate-label prose rejection; readable escaping of
apostrophes/source newlines; stale-result localized status; unsafe renamed
basenames rejected before write. Existing shared writer/rendering tests were
rerun after those changes.

The final review reads the complete diff from accepted Phase 1B and actual
generated Markdown, not just test results. Final acceptance evidence and
isolation observations follow below.

## Validation evidence

- Required focused authority/Obsidian/Note V2/Backup/Restore/API set: 211 passed
  before the last unsafe-basename case; the final focused filesystem/rendering
  set includes it and passed **88 tests**.
- Phase 2 collection: **39 cases**, all covered by final focused/full runs.
- Final full backend: **3,030 passed, 1 skipped, 2 warnings**, 415.16s.
  The unchanged optional golden-token-id test requires an explicitly
  provisioned canonical o200k asset (`YOUTUBE_INTEL_O200K_TEST_ASSET`). No test
  was removed, newly skipped or weakened. Warnings are the intentional
  duplicate-path backup fixture and an existing model-construct bypass test.
- Ruff: `ruff check .`, passed.
- Strict mypy: `python -m mypy --strict src`, 71 source files passed.
- Compile: `python -m compileall -q src tests scripts`, passed.
- `git diff --check`, passed.
- Frontend: typecheck passed; **106 tests passed** (74 workspace, 32 demo);
  production build passed, 35 modules. A React act warning in the existing
  Chinese Deep Analysis POST-failure test is non-failing; it was not suppressed.
- Real Chrome: **9 HTTP/SQLite/vault scenarios**, keyboard explicit publish,
  NOT_QUALIFIED independence, owner-edit replacement, no automatic POST, and
  English/Chinese at 320/768/1024/1440px. Zero console errors/overflow.
- Existing Phase 1B Chrome regression: **16 scenarios**, zero console
  errors/overflow. Navigation remains six destinations.

Commands use the existing `/Users/hua/youtube-intel/.venv` and existing frontend
dependencies; `PYTHONPATH=src` selects this independent source tree. The owned
temporary node_modules symlink is removed after validation. Local evidence:
`/tmp/v1x-phase2-{acceptance-focused,focused-final,full-backend-acceptance,frontend-final,build-final,browser-final,phase1b-browser-final}.log`.
Browser screenshots are in `/tmp/v1x-phase2-browser-real-2/screenshots`.
Earlier incomplete full runs were interrupted to review/remediate changed code
and are superseded; they are not counted as full-validation passes.

## Isolation and commits

Before/after audits are read-only HEAD, porcelain status, dirty/untracked file
hashes and `git diff HEAD` hashes. Raw snapshots are local
`/tmp/v1x-phase2-isolation-{before,after,final}.json`.

- M13: HEAD `e228294f705401b0200439076c3378b78f9c9d84`, 35 initial dirty/untracked
  entries. Its complete after snapshot is identical; diff SHA256
  `75e720ea3e96d659f259aef256bde0cc73ded747b86eb7aa7c223216597f501b`.
- Phase 1C: initial HEAD `31c2ff59b594ca15b8f5e38ba813b0e81bed0abe`, 15 initial
  entries, initial diff SHA256
  `29c454c598c03d007d0d6691ba23f239e7786c638c63c34680bbc53fb0ea2722`.
  Final HEAD is unchanged; the independent worker continued editing (21 entries
  at the final audit), final diff SHA256
  `5fcbc7be6bc3e9acde2aacff9c3381c40fe348f7a6a30740745daf10df8893ee`.
  This is not an identical-state claim. This executor made no writes, copied
  no uncommitted code and did not merge that worktree.

Scoped local commits:

1. `c41ad02583395d1357a0b056d4cb36242ce1c981` — explicit trusted DA projection.
2. `94c7e59f7cb8f9b9a34f04602c8303d36fb1c910` — reviewed writer/ownership
   remediation, adversarial coverage, decision record and browser harness.
3. Acceptance documentation commit — final HEAD reported in the final response.

Final validation passed on implementation commit `94c7e59`. The last commit
adds only this acceptance record. The fresh accepted-baseline diff and actual
generated Markdown review found no remaining P0/P1 or material in-scope P2
defect. Task-owned fixture/Vite processes were stopped and only the owned
node_modules symlink was removed. Final git status is clean. No genuine
remaining blockers; Phase 3 or integration may proceed.
