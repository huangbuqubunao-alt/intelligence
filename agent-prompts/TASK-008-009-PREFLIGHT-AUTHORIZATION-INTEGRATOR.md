# TASK-008 / TASK-009 read-only preflight authorization sync

Role: Status Integrator. Work only in `/Users/developer/Documents/youtubek agent`.

This is a control-plane-only task. Commit two independent read-only Scout packets for
TASK-008 and TASK-009. Do not create worktrees/branches, change task states, install or
resolve dependencies, run product commands, access credentials or Vaults, start Scouts,
push, merge, or clean anything.

## Fixed inputs

- Required main: `main@37819ec24da6e1a61d635dd36f269aff0e62a005`
- Git identity: `Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`
- TASK-006=`DONE`
- TASK-007=`DONE`
- TASK-008=`BLOCKED/UNASSIGNED`
- TASK-009=`BLOCKED/UNASSIGNED`

Verify main branch/HEAD/identity, an empty initial index, and no existing worktree or branch
for TASK-008/TASK-009. Both tasks have their code dependencies satisfied, but their
contract/resource/dependency approvals remain unsatisfied; this packet is not an
implementation authorization.

## Prepared files and commit

The prepared-control exception applies. Main is expected to contain exactly these seven
unstaged modified/untracked Markdown files:

1. `agent-prompts/TASK-008-009-PREFLIGHT-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/PREFLIGHT-TASK-008-READONLY.md`
3. `agent-prompts/PREFLIGHT-TASK-009-READONLY.md`
4. `docs/PROJECT_STATUS.md`
5. `tasks/README.md`
6. `tasks/TASK-008-deep-analysis.md`
7. `tasks/TASK-009-obsidian-notes.md`

Record SHA-256 for all seven before staging. Verify exact combined scope, complete Diff,
LF at EOF, trailing whitespace and `git diff --check`, including all untracked prompt
files. Confirm:

- TASK-008 and TASK-009 remain `BLOCKED/UNASSIGNED`;
- both Scout packets are strictly read-only and may run in parallel;
- neither packet grants dependencies, lockfile changes, network research, API calls,
  secret access, real Vault access, file writes, worktrees, implementation or task state;
- TASK-006 and TASK-007 remain `DONE`;
- no downstream task is unlocked.

Stage only the seven files. Repeat hashes, compare staged blobs, run
`git diff --cached --check`, and verify exact cached scope with no unstaged content. Any
extra path, pre-existing index content, changed hash, identity/status mismatch, or
concurrent change blocks the commit without cleanup, overwrite, restage, or commit.

Commit:

```text
docs: authorize TASK-008 and TASK-009 read-only preflights
```

After commit verify:

- it has sole parent `37819ec24da6e1a61d635dd36f269aff0e62a005`;
- committed scope is exactly the seven files;
- each preflight prompt resolves dynamically to the new commit with
  `git log -1 --format=%H -- <prompt path>`;
- main is clean and no TASK-008/TASK-009 worktree or branch was created.

Do not start either Scout. Report base/head, identity, files, checks, both dynamic
authorizations, unchanged task states, post-commit cleanliness, verdict and remaining
approval gaps.
