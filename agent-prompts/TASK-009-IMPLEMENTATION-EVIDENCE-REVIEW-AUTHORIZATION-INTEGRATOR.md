# TASK-009 实现证据与审查授权同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控预写的 TASK-009 审查控制面；不得实现、审查、合并、rebase、push、清理 source/worktree，且不得运行 `uv`、pytest、mypy、Ruff、build、网络、数据库或产品命令。

## 固定事实

- Main：`/Users/hua/Documents/youtubek agent` / `main@83bd1f1fcfdef5d4949f59b513033803113c3d8a`
- Source：`/Users/hua/Documents/yia-worktrees/task-009` /
  `codex/task-009-obsidian-notes@956e37a15ab29106f16c45873fccb813cc5a959f`
- Source base：`473119704c7638d7afd4e68d84d00e85064ceabd`；implementation commit 的唯一父必须是该 base。
- 身份必须是 `Mozhu <huangbuqubunao@gmail.com>` 且 `user.useConfigOnly=true`。
- Source worktree 的 `tasks/` 与 `docs/PROJECT_STATUS.md` 是分配前固定快照；实时 TASK-009=`IN_REVIEW` 仅以 main 的本次提交和 Reviewer 包为准，历史状态不得视为冲突或写回 source。

## 唯一允许提交范围

仅以下五个主控预写 Markdown 文件；内容与 SHA-256 在检查期间必须稳定：

1. `agent-prompts/TASK-009-IMPLEMENTATION-EVIDENCE-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-009-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-009-obsidian-notes.md`

初始 main 只能有上述五个未提交变更，暂存区必须为空。任何额外/并发变更、哈希变化、身份、父链、范围或内容冲突，均立即 `BLOCKED`，不得覆盖、重新生成、取消暂存或清理。TASK-008 source 是独立审查 worktree，不得读取、等待、修改、暂存或清理。

## 必须核验

1. Source branch/HEAD/唯一父/洁净度精确匹配；source 相对 base 的完整 Diff 只包含：
   `src/youtube_intel/notes.py`、`src/youtube_intel/providers/obsidian.py`、
   `src/youtube_intel/templates/video.md`、`tests/fixtures/notes/**`、
   `tests/unit/test_note_rendering.py`、`tests/integration/test_obsidian_sink.py`、`handoffs/TASK-009.md`。
2. 无 `domain.py`、`config.py`、`state.py`、Schema/migration、依赖、锁文件、CLI、云 Provider、任务状态或 TASK-008 变更；source Diff 和 main Diff 均通过 `git diff --check`。
3. 仅记录 Implementer 自报的 lock/sync、focused `4/6`、full pytest `337`、mypy、Ruff、CLI、offline build、模板/migration package inclusion、临时 Vault 原子写与 SQLite 补账证据；这些不构成 Reviewer 结论。
4. TASK-009 设为 `IN_REVIEW`，全新独立 Codex Reviewer 只可向 source `handoffs/TASK-009.md` 追加审查证据；不得预写 verdict、ACCEPTED、merge 或 DONE。
5. TASK-008 保持 `IN_REVIEW` 且不触碰；真实 Vault、用户笔记、测试目录外写入、外部文件删除、凭据、云端和网络路径继续未授权。

执行身份/分支/HEAD/索引、source parent/range/cleanliness、五文件双轮 SHA-256、LF-at-EOF、尾随空白、`git diff --check`、暂存范围与 `git diff --cached --check`；不得运行产品命令。

全通过后只创建一个单父提交：

```text
docs: authorize TASK-009 independent review
```

回传 `Task/Role/Base/Head/identity/source/scope/status/reviewer authorization/Post-commit status/Verdict/remaining risks`。
