# TASK-008/TASK-009 并行分配同步 — Worktree / Status Integrator

你是全新的 Codex Worktree / Status Integrator。你只创建两份批准的 worktree、提交主控预写的分配控制面；不得实现、审查、合并、rebase、push、清理任何 source/worktree，且不得运行 `uv`、pytest、mypy、Ruff、build、网络、数据库或产品命令。

## 固定授权

- Main：`/Users/hua/Documents/youtubek agent` / `main@473119704c7638d7afd4e68d84d00e85064ceabd`
- 身份必须是 `Mozhu <huangbuqubunao@gmail.com>` 且 `user.useConfigOnly=true`。
- TASK-008：创建 `/Users/hua/Documents/yia-worktrees/task-008`，分支 `codex/task-008-deep-analysis`，固定于 base；Codex Implementer，完成后全新独立 Codex Reviewer。
- TASK-009：创建 `/Users/hua/Documents/yia-worktrees/task-009`，分支 `codex/task-009-obsidian-notes`，固定于同一 base；Codex Implementer，完成后全新独立 Codex Reviewer。
- 两项可并行，范围不重叠。TASK-008 只允许离线 Fake/子进程隔离 SDK 实现与测试，禁止真实 OpenAI、密钥、付费/API 调用。TASK-009 只允许测试临时目录内的原子写、替换、清理与 symlink 安全测试，禁止真实 Obsidian Vault、真实用户笔记与外部文件删除。

## 唯一允许提交范围

仅以下八个主控预写 Markdown 文件；内容与 SHA-256 在检查期间必须稳定：

1. `agent-prompts/TASK-008-009-ASSIGNMENT-INTEGRATOR.md`
2. `agent-prompts/TASK-008-IMPLEMENTER-CODEX.md`
3. `agent-prompts/TASK-009-IMPLEMENTER-CODEX.md`
4. `docs/PRODUCT_DECISIONS.md`
5. `docs/PROJECT_STATUS.md`
6. `tasks/README.md`
7. `tasks/TASK-008-deep-analysis.md`
8. `tasks/TASK-009-obsidian-notes.md`

初始 main 只能有上述八个未提交变更，暂存区必须为空；两个目标分支/worktree 路径必须均不存在。任何额外/并发变更、哈希变化、身份、基线、范围或内容冲突，均立即 `BLOCKED`，不得覆盖、重新生成、取消暂存或清理。

## 执行与核验

1. 核验 main 分支/HEAD、身份、空索引、八文件范围、LF/EOF/尾随空白和双轮 SHA-256。
2. 创建目录父级后，依次执行：

```bash
git worktree add "/Users/hua/Documents/yia-worktrees/task-008" -b codex/task-008-deep-analysis 473119704c7638d7afd4e68d84d00e85064ceabd
git worktree add "/Users/hua/Documents/yia-worktrees/task-009" -b codex/task-009-obsidian-notes 473119704c7638d7afd4e68d84d00e85064ceabd
```

3. 核验两份 source worktree 的分支、HEAD、洁净度；两份 source 卡仍显示旧 `BLOCKED/UNASSIGNED` 是预期冻结快照，main 的本提交和绝对路径 Implementer 包才是实时授权。
4. 核验 TASK-008/TASK-009 各自任务卡的七路径范围、无 `domain.py`/`config.py`/`state.py`/Schema/migration/依赖/锁文件交集；TASK-008 禁止父进程导入 SDK、真实凭据和网络，TASK-009 禁止真实 Vault 与测试目录外写入。
5. 执行 `git diff --check`、暂存精确八文件、`git diff --cached --check`，再创建唯一单父提交：

```text
docs: assign TASK-008 and TASK-009 worktrees
```

提交后 main 与两个 source worktree 必须干净。不得启动 Implementer/Reviewer；不得运行产品命令。

回传 `Task/Role/Base/Head/identity/worktree/branch/source cleanliness/精确提交范围/状态/禁止项/Post-commit status/Verdict/remaining risks`。
