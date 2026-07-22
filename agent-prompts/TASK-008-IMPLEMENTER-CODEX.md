# TASK-008 — Codex Implementer

你是 TASK-008 的唯一 Codex Implementer。任务已由 main 控制面正式分配；source 卡片保留的 `BLOCKED/UNASSIGNED` 是固定 base 快照，实时授权以本包和 main 中 TASK-008=`IN_PROGRESS` 为准。

## 固定对象

- Main authorization：动态读取 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-008-IMPLEMENTER-CODEX.md`
- Base：`473119704c7638d7afd4e68d84d00e85064ceabd`
- Worktree/branch：`/Users/hua/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis`
- Allowed scope：`src/youtube_intel/analysis.py`、`src/youtube_intel/providers/cloud_llm.py`、`src/youtube_intel/prompts/summary.md`、`tests/fixtures/analysis/**`、`tests/unit/test_analysis_policy.py`、`tests/integration/test_summary_provider.py`、`handoffs/TASK-008.md`。
- Reuse：`DIRECT` official OpenAI SDK/tiktoken already locked by TASK-008A; existing domain/Artifact/Provider-call/SQLite contracts. No handwritten HTTP client, second Provider, SDK retry, format-repair call, token-count endpoint, or real credential/API.

## Approved boundary and checks

- Only offline Fake transport and synthetic sentinels. The SDK may be imported only by a whitelist-environment isolated child process; never import it in the main process.
- Do not read a real key, load any secret, call an API, consume paid capacity, invoke a cloud token-count endpoint, or touch a real Vault/user content/media/network path.
- No dependency/lockfile, shared-domain/config, state/Schema/migration, CLI or task-status changes.
- Implement ADR-008 A-01 to A-17 and TASK-008 AC within scope. Required commands: `uv lock --check`; `uv sync --locked`; focused unit and integration tests named by the task card; full pytest; mypy; Ruff; CLI help; `uv build --offline`; and `git diff --check 473119704c7638d7afd4e68d84d00e85064ceabd...HEAD`.
- Verify sdist/wheel migration inclusion, exact seven scope groups, and handoff reuse/license evidence; commit once and report SHA. Do not merge or alter task status. Any public-contract, dependency, real-resource or out-of-scope need is `DECISION NEEDED`.
