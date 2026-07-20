# TASK-008 / TASK-009 ADR proposal sync

Role: Status Integrator. Work only in `/Users/hua/Documents/youtubek agent`.

This is a control-plane-only task. Commit the prepared ADR-008/ADR-009 proposals,
TASK-008A/TASK-009A task cards and related planning updates exactly as prepared. Do not
approve decisions, install/resolve dependencies, create worktrees/branches, run product
commands, access credentials/Vaults, call networks, start Workers, push, merge or clean
anything.

## Fixed inputs

- Required main: `main@bb9c6b7bb66040b65b091d980f43281c4d9d6ba6`
- Git identity: `Mozhu <huangbuqubunao@gmail.com>`
- `user.useConfigOnly=true`
- TASK-006=`DONE`
- TASK-007=`DONE`
- TASK-008A/TASK-009A/TASK-008/TASK-009=`BLOCKED/UNASSIGNED`
- ADR-008/ADR-009=`Proposed`

Verify main branch/HEAD/identity and an empty initial index. No TASK-008A, TASK-009A,
TASK-008 or TASK-009 worktree/branch may exist. The two read-only preflights are complete
and made no repository changes.

## Prepared files and commit

The prepared-control exception applies. Main is expected to contain exactly these twelve
unstaged modified/untracked Markdown files:

1. `agent-prompts/TASK-008-009-ADR-PROPOSAL-INTEGRATOR.md`
2. `docs/IMPLEMENTATION_ROADMAP.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/REUSE_REGISTER.md`
5. `docs/decisions/ADR-008-cloud-analysis-contract.md`
6. `docs/decisions/ADR-009-obsidian-note-contract.md`
7. `docs/decisions/README.md`
8. `tasks/README.md`
9. `tasks/TASK-008A-cloud-analysis-shared-contracts.md`
10. `tasks/TASK-008-deep-analysis.md`
11. `tasks/TASK-009A-obsidian-note-shared-contracts.md`
12. `tasks/TASK-009-obsidian-notes.md`

Record SHA-256 for all twelve before staging. Verify exact combined scope, complete Diff,
LF at EOF, trailing whitespace and `git diff --check`, including every untracked file.
Confirm the prepared content is internally consistent:

- ADR-008 has exactly A-01 through A-15 and remains `Proposed`;
- ADR-009 has exactly N-01 through N-15 and remains `Proposed`;
- TASK-008A depends on TASK-007; TASK-009A depends on TASK-008A;
- formal TASK-008 depends on TASK-008A/TASK-009A and formal TASK-009 depends on TASK-009A;
- TASK-008A owns the proposed OpenAI/tiktoken dependency baseline, TASK-009A later owns
  the proposed Jinja2 dependency baseline; formal TASK-008/TASK-009 do not own
  `pyproject.toml`/`uv.lock` and may only run in parallel after both shared tasks are DONE;
- recommended ranges are exactly `openai>=2.46.0,<2.47`,
  `tiktoken>=0.13.0,<0.14` and `Jinja2>=3.1.6,<3.2`;
- all three dependencies remain `DIRECT-PENDING`; this commit is not installation,
  lockfile, download or implementation approval;
- all four tasks remain `BLOCKED/UNASSIGNED`, with no base/worktree/branch/role assignment;
- no real OpenAI/token-count API, secret/env-value, real Vault/user note, model, media,
  YouTube, ffmpeg or other real-resource authorization is introduced;
- no Schema/migration/`state.py` change is proposed for these V1 slices;
- TASK-006/TASK-007 remain `DONE` and no downstream task is unlocked.

Stage only the twelve files. Repeat hashes, compare staged blobs, run
`git diff --cached --check`, and verify exact cached scope with no unstaged content. Any
extra path, pre-existing index content, changed hash, identity/status mismatch, missing or
duplicate decision section, concurrent change or content conflict blocks the commit
without cleanup, overwrite, restage or commit.

Commit:

```text
docs: propose cloud analysis and note contracts
```

After commit verify:

- it has sole parent `bb9c6b7bb66040b65b091d980f43281c4d9d6ba6`;
- committed scope is exactly the twelve files;
- this prompt resolves dynamically to the new commit with
  `git log -1 --format=%H -- agent-prompts/TASK-008-009-ADR-PROPOSAL-INTEGRATOR.md`;
- main is clean and no task worktree/branch was created.

Do not run tests, uv, builds or imports. Do not approve either ADR or start any task.
Report base/head, identity, files, checks, ADR/task states, dependency proposal status,
post-commit cleanliness, verdict and remaining product approvals.
