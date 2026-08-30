# TASK-014B9 — Product-owner one-shot reauthorization executor

## Authorization identity

- Task: `TASK-014B9` replacement public-sample directory-only qualification.
- Role: Smoke Executor.
- Fresh source baseline: `main@947c407d1cfec692bcb3cd175e1bdddcd13d6525`.
- Source worktree: `/Users/hua/Documents/yia-worktrees/task-014b9-po-one-shot-qualification`.
- Source branch: `codex/task-014b9-po-one-shot-qualification`.
- Reuse decision: `DIRECT` — use the integrated B4 `smoke-public-subtitles --directory-only` entrypoint, locked yt-dlp Adapter, safe-summary outlet, and ADR-017 through ADR-021 boundaries. No dependency or product-code change is authorized.

This is a new product-owner authorization, not a continuation of the historical package.
Historical authorization `e975ff4` is consumed; its direct child `bd770ef` records one
execution that stopped with `CONTENT_UNAVAILABLE` after `metadata=1`, `enumerate=1`, and
`read=0`. Both commits remain preserved and unmodified.

## Frozen qualification boundary

- Sample: `eIho2S0ZahI`.
- Selection mode: same public replacement candidate under this separate authorization.
  The historical result did not permanently disqualify the candidate, and reusing the fixed
  candidate avoids a new search or sample substitution. It is not a retry under `e975ff4`.
- Semantic attempts: exactly `1`; semantic retries: `0`; post-start substitutions: `0`.
- Timeout: the existing fixed `30`-second network-call timeout; no escalation.
- Entry point: only this worktree's absolute `.venv/bin/youtube-intel` launcher, after
  `uv lock --check`, `uv sync --locked --offline`, and a second `uv lock --check` pass.
- Invocation: one `smoke-public-subtitles --directory-only` command with one newly created,
  nonexistent absolute `smoke-root` child. The command must perform `metadata=1`,
  `enumerate=1`, and `read=0`.

The invocation may access only the specified public video through the existing metadata and
subtitle-directory paths. It must not authenticate, read subtitle bodies, download media,
use user data, access a Vault, invoke models or paid services, or issue another product
command. The temporary root is inspected only with safe relative paths and cleaned only when
it was created by this invocation. Evidence may retain only the approved safe summary fields;
never raw output, paths, URLs, titles, subtitle content, exception text, or credentials.

Any nonzero exit, wrong counts, leaked output, directory-contract failure, or unavailable
content consumes this new authorization and stops live execution. It does not authorize a
retry, a different sample, a timeout change, or a source fix followed by another live call.
