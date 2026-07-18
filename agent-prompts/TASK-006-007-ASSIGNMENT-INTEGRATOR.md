# TASK-006 / TASK-007 Assignment — Worktree and Status Integrator

## Authority

Product-owner approval authorizes this exact parallel assignment from
`main@6b4d59c882ccdcbd0e5a6069a6661e0672921a80`. You are the only writer to main
for this control-plane sync. Do not run uv, tests, builds, model/service/network/media commands,
or modify product source.

## Create and verify worktrees

1. Require main branch, exact base, empty index, correct identity and
   `user.useConfigOnly=true`. The initial working tree is an explicit authorized
   exception to the usual cleanliness rule: it must contain exactly the eight
   **Allowed main files** below as uncommitted control-plane preparation and no
   other tracked or untracked paths. Record SHA-256 values before proceeding and
   require them to remain stable until staging.
2. Require that neither branch nor path exists before creation:
   - `/Users/hua/Documents/yia-worktrees/task-006` / `codex/task-006-local-transcription`
   - `/Users/hua/Documents/yia-worktrees/task-007` / `codex/task-007-local-scoring`
3. Create both from the exact base. Verify each HEAD equals the base and both worktrees are clean.
   They are isolated writers and may run in parallel.

## Allowed main files

1. `agent-prompts/TASK-006-007-ASSIGNMENT-INTEGRATOR.md`
2. `agent-prompts/TASK-006-IMPLEMENTER-CODEX.md`
3. `agent-prompts/TASK-007-IMPLEMENTER-CODEX.md`
4. `docs/PRODUCT_DECISIONS.md`
5. `docs/PROJECT_STATUS.md`
6. `tasks/README.md`
7. `tasks/TASK-006-local-transcription.md`
8. `tasks/TASK-007-local-scoring.md`

## Content gates

- TASK-006 must be `IN_PROGRESS`/Codex. It alone may modify `pyproject.toml` and `uv.lock`, and
  may install only `mlx-whisper>=0.4.3,<0.5` plus required transitive packages. Its Phase A must
  remain model-free, ffmpeg-free, media-free and smoke-free.
- TASK-007 must be `IN_PROGRESS`/Codex. It must not modify dependencies or lockfiles and may use
  only offline Fake/test-local HTTP behavior, never a real Ollama service.
- Both source snapshots retain historical `BLOCKED` cards because they are created from the fixed
  base. The dynamic main assignment commit is the explicit live control plane; each Implementer
  packet must resolve to this commit before it writes.
- Both Reviewer roles are fresh independent Codex sessions and must remain waiting for source
  commits; do not generate premature reviewer evidence or status.
- Preserve all real-resource denials: model/weight download or loading, Ollama install/start/model
  pull/real call, ffmpeg, media/YouTube, auth/Cookie, remote components, Vault/secrets and deletion.

## Required Git checks and commit

1. Verify the initial/staged/committed scope is exactly the eight Allowed main files; hashes must
   remain stable during checks. The prepared initial scope is authorized and must be committed as
   is; do not discard, reset, restore, or recreate it.
2. Run `git diff --check`, trailing-whitespace/EOF checks and `git diff --cached --check`.
3. Commit only these files with `docs: assign TASK-006 and TASK-007 parallel worktrees`.
4. Confirm main is clean and each source worktree remains clean at the fixed base. Do not start the
   Implementers, merge, push, remove worktrees or alter ignored build artifacts.
