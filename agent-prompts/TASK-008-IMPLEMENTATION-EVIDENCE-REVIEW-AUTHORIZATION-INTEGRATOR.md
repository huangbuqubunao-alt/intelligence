# TASK-008 实现证据与审查授权同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控预写的 TASK-008 审查控制面；不得实现、审查、合并、rebase、push、清理 source/worktree，且不得运行 `uv`、pytest、mypy、Ruff、build、网络、数据库或产品命令。

## 固定事实

- Main：`/Users/developer/Documents/youtubek agent` / `main@6ff45f196ed2229d21482e8df1594e96c036f7d8`
- Source：`/Users/developer/Documents/yia-worktrees/task-008` /
  `codex/task-008-deep-analysis@10478a9083df4eedae061d99d941c88cb4954179`
- Source base：`473119704c7638d7afd4e68d84d00e85064ceabd`；implementation commit 的唯一父必须是该 base。
- 身份必须是 `Mozhu <maintainer@example.invalid>` 且 `user.useConfigOnly=true`。
- Source worktree 中的 `tasks/` 与 `docs/PROJECT_STATUS.md` 是分配前固定快照；实时 TASK-008=`IN_REVIEW` 状态仅以 main 的本次提交和 Reviewer 包为准，历史状态不得视为冲突或写回 source。

## 唯一允许提交范围

仅以下五个主控预写 Markdown 文件；内容与 SHA-256 在检查期间必须稳定：

1. `agent-prompts/TASK-008-IMPLEMENTATION-EVIDENCE-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-008-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

初始 main 只能有上述五个未提交变更，暂存区必须为空。任何额外/并发变更、哈希变化、身份、父链、范围或内容冲突，均立即 `BLOCKED`，不得覆盖、重新生成、取消暂存或清理。TASK-009 source 是独立活跃 worktree，不得读取、等待、修改、暂存或清理。

## 必须核验

1. Source branch/HEAD/唯一父/洁净度精确匹配；source 相对 base 的完整 Diff 只包含：
   `src/youtube_intel/analysis.py`、`src/youtube_intel/providers/cloud_llm.py`、
   `src/youtube_intel/prompts/summary.md`、`tests/fixtures/analysis/**`、
   `tests/unit/test_analysis_policy.py`、`tests/integration/test_summary_provider.py`、`handoffs/TASK-008.md`。
2. 无 `domain.py`、`config.py`、`state.py`、Schema/migration、依赖、锁文件、CLI、任务状态或 TASK-009 变更；source Diff 和 main Diff 均通过 `git diff --check`。
3. 仅记录 Implementer 自报的 lock/sync、full pytest `340`、mypy、Ruff、CLI、offline build、SQLite 原子回滚/重排零调用/30 天 retention 证据；这些不构成 Reviewer 结论。
4. TASK-008 设为 `IN_REVIEW`，全新独立 Codex Reviewer 只可向 source `handoffs/TASK-008.md` 追加审查证据；不得预写 verdict、ACCEPTED、merge 或 DONE。
5. TASK-009 保持 `IN_PROGRESS` 且不触碰；真实 OpenAI、密钥、付费/API 调用、网络、真实 Vault、用户笔记和外部文件操作继续未授权。

执行身份/分支/HEAD/索引、source parent/range/cleanliness、五文件双轮 SHA-256、LF-at-EOF、尾随空白、`git diff --check`、暂存范围与 `git diff --cached --check`；不得运行产品命令。

全通过后只创建一个单父提交：

```text
docs: authorize TASK-008 independent review
```

回传 `Task/Role/Base/Head/identity/source/scope/status/reviewer authorization/Post-commit status/Verdict/remaining risks`。
