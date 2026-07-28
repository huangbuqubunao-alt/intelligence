# TASK-014 Phase B-1 Directory-only Public YouTube Smoke Evidence

- Date: `2026-07-28`
- Execution baseline: `main@9bffb29d84868c94fc8544395183c5472856e7c8`
- Source branch/HEAD: `codex/task-014-phase-b1-directory-only-execution` /
  `9bffb29d84868c94fc8544395183c5472856e7c8`
- Reuse decision: `DIRECT` — existing installed `youtube_intel.cli:main` entry point,
  restricted `smoke-public-subtitles --directory-only` mode, and release-evidence
  documents; no dependency or third-party code change.

## Preconditions

| Check | Result | Safe evidence |
|---|---|---|
| Source branch, HEAD, and initial worktree cleanliness | PASS | Matched the assigned branch and required HEAD; no initial worktree changes. |
| `uv lock --check` (before sync) | PASS | Exit `0`; resolved 84 locked packages. |
| `uv sync --locked --offline` | PASS | Exit `0`; completed using the locked offline environment. |
| `uv lock --check` (after sync) | PASS | Exit `0`; resolved 84 locked packages. |
| Absolute launcher static verification | PASS | Exists, is executable, and imports `youtube_intel.cli:main`. |
| Temporary-root precondition | PASS | A new temporary parent existed and its `smoke-root` child did not exist as a file, directory, or symlink before invocation. The absolute path is intentionally not retained. |

## Single Authorized Invocation

- Invocation count: `1` (no retry, loop, concurrent execution, alternative entry point, or other product command).
- Fixed IDs, in authorized order: `--khbXchTeE`, `JTxsNm9IdYU`.
- Mode: `smoke-public-subtitles --directory-only` with the newly verified temporary root.
- Exit code: `1` (`FAIL`).
- Fixed diagnostic code: `not emitted in the permitted sanitized output`.

## Per-ID Budget Evidence and Stop Point

| Fixed ID | metadata | enumerate | read | Evidence status |
|---|---:|---:|---:|---|
| `--khbXchTeE` | not attestable | not attestable | not attestable | The one permitted invocation exited `1` without an allowed, sanitized per-ID counter. No count is inferred. |
| `JTxsNm9IdYU` | not attestable | not attestable | not attestable | The one permitted invocation exited `1` without an allowed, sanitized per-ID counter. No count is inferred. |

The execution stopped immediately at the non-zero result. No subtitle body, media, Cookie,
authentication material, Vault or user data, model, OpenAI, or other restricted resource was
read or invoked by this executor after that stop point. The lack of attestable per-ID counters
means this evidence cannot demonstrate the required `1/1/0` budgets. TASK-014 remains
`IN_PROGRESS / No-Go`; this is not a release approval or a successful real-service validation.
