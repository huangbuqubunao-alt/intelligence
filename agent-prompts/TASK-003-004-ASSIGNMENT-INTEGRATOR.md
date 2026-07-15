# TASK-003/TASK-004 Parallel Assignment Sync

## 身份与边界

你是原 `main` 控制面终端中的 Status Integrator。本轮只核对并提交主控已准备好的 TASK-003/TASK-004 worktree、角色、Implementer 包和 `IN_PROGRESS` 状态；不得修改内容、运行产品代码、安装依赖、写任务 worktree、启动 Implementer 或生成 Reviewer commit。

## 固定基线

- Task: `TASK-003/TASK-004 assignment sync`
- Role: `Status Integrator`
- Required base: `main@dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Main worktree: `/Users/hua/Documents/youtubek agent`
- TASK-003 worktree: `/Users/hua/Documents/yia-worktrees/task-003`，严格只读
- TASK-003 branch: `codex/task-003-state-store`
- TASK-004 worktree: `/Users/hua/Documents/yia-worktrees/task-004`，严格只读
- TASK-004 branch: `grok/task-004-discovery-metadata`
- Both required worktree HEADs: `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Suggested commit: `docs: assign TASK-003 and TASK-004 implementations`

开始前按顺序完整读取 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/REUSE_REGISTER.md`、`tasks/README.md`、两张任务卡和本轮三个新任务包。任一文件冲突、基线不符或范围异常时立即停止，不自行修订内容。

## 唯一允许提交的 7 个文件

- `agent-prompts/TASK-003-004-ASSIGNMENT-INTEGRATOR.md`
- `agent-prompts/TASK-003-IMPLEMENTER-CODEX.md`
- `agent-prompts/TASK-004-IMPLEMENTER-GROK.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-003-state-store.md`
- `tasks/TASK-004-discovery-metadata.md`

初始 `git status --short` 必须只包含上述 7 个文件且没有 staged 内容。出现额外文件、并发写入、任务 worktree 变化或文件在检查期间变化，立即输出 `BLOCKED`；不得清理、覆盖、取消暂存或吸收其他人的修改。

## 必须确认的事实

1. main 精确位于 `dcc7d85...` 且干净基线上只存在 7 个准备文件。
2. TASK-003 worktree 存在、干净、分支/HEAD 精确匹配；TASK-004 同理。
3. 两个 worktree 都继承 `user.useConfigOnly=true` 与 `Mozhu <huangbuqubunao@gmail.com>`。
4. TASK-003=`IN_PROGRESS`：Codex 是唯一 Implementer，Grok 仅等待实现 commit；允许范围精确为 5 个文件，不新增依赖、不改 `pyproject.toml/uv.lock/domain.py`。
5. TASK-004=`IN_PROGRESS`：Grok 是唯一 Implementer，Codex 仅等待实现 commit；只允许已批准的 `yt-dlp[default,deno]>=2026.7.4,<2026.8` 及必要传递依赖和锁文件动作。
6. 两个 Implementer 包都绑定同一 base，但使用不同 worktree、分支和写入范围；没有占位符，没有让一方等待另一方完成。
7. 两个包均包含 ADR-005 `Reuse decision`、文件范围、验证命令、交接与 commit 要求。
8. TASK-004 明确禁止真实 YouTube 冒烟、Cookie、账号登录、remote components、ffmpeg 和媒体/字幕下载。
9. Reviewer 包尚未生成，Reviewer 不得现在启动；任一任务先完成时可先进入该任务独立审查，另一个 Implementer 继续运行。
10. TASK-005 及后续写入任务仍为 `BLOCKED`。

## 只读检查

在 main 运行：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git config --get user.useConfigOnly
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
git diff --check
git diff --name-status
```

分别只读核对 worktree：

```bash
git -C "/Users/hua/Documents/yia-worktrees/task-003" branch --show-current
git -C "/Users/hua/Documents/yia-worktrees/task-003" rev-parse HEAD
git -C "/Users/hua/Documents/yia-worktrees/task-003" status --short
git -C "/Users/hua/Documents/yia-worktrees/task-003" config --get user.useConfigOnly
git -C "/Users/hua/Documents/yia-worktrees/task-003" var GIT_AUTHOR_IDENT
git -C "/Users/hua/Documents/yia-worktrees/task-004" branch --show-current
git -C "/Users/hua/Documents/yia-worktrees/task-004" rev-parse HEAD
git -C "/Users/hua/Documents/yia-worktrees/task-004" status --short
git -C "/Users/hua/Documents/yia-worktrees/task-004" config --get user.useConfigOnly
git -C "/Users/hua/Documents/yia-worktrees/task-004" var GIT_AUTHOR_IDENT
```

若身份为空、含 `.local` 或不匹配批准身份，立即停止。检查三个新任务包不存在未替换的尖括号模板占位符、模板任务编号或模板字段；不得编辑发现的问题。

## 内容核对

- `docs/PROJECT_STATUS.md` 的 worktree、共同 base、角色、并行组和下一步一致。
- `tasks/README.md` 门禁为 `TASK_003_004_IN_PROGRESS`，表内角色和状态一致。
- TASK-003 卡记录 base/worktree/branch/Codex Implementer/Grok Reviewer waiting。
- TASK-004 卡记录 base/worktree/branch/Grok Implementer/Codex Reviewer waiting。
- TASK-003 包要求标准库 SQLite `DIRECT`，禁止 ORM、依赖和锁文件修改，完整覆盖 ADR-003 S-01 至 S-08。
- TASK-004 包要求官方 yt-dlp `DIRECT`，只参考已登记候选，完整覆盖 ADR-004 D-01 至 D-08 和未授权行为。
- 两包都说明：本地任务卡仍显示 `READY/UNASSIGNED` 是 worktree 基线隔离的预期结果，不得 cherry-pick 本次状态提交。

## 暂存与提交

只暂存上述 7 个文件，随后运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
git status --short
```

`git diff --name-only` 必须无输出；暂存范围精确为 7 文件。提交：

```bash
git commit -m "docs: assign TASK-003 and TASK-004 implementations"
```

提交后运行：

```bash
git status --short
git rev-parse HEAD
git rev-parse HEAD^
git diff --name-status dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176..HEAD
git log -1 --format='author=%an <%ae>%ncommitter=%cn <%ce>'
git -C "/Users/hua/Documents/yia-worktrees/task-003" status --short
git -C "/Users/hua/Documents/yia-worktrees/task-003" rev-parse HEAD
git -C "/Users/hua/Documents/yia-worktrees/task-004" status --short
git -C "/Users/hua/Documents/yia-worktrees/task-004" rev-parse HEAD
```

确认新提交是 `dcc7d85...` 的单父后继、范围精确为 7 个文件、main 干净；两个任务 worktree 仍干净且保持共同 base。不得启动任何 Implementer；等待用户在独立终端执行两份任务包。

## 返回格式

```text
Task: TASK-003/TASK-004 assignment sync
Role: Status Integrator
Base:
Head commit:
Git identity:
Checks:
- Initial/staged scope:
- TASK-003 worktree/status/roles/packet:
- TASK-004 worktree/status/roles/packet:
- Reuse and approval boundaries:
- Parallel isolation:
- git diff checks:
Committed files:
Final states: TASK-003=IN_PROGRESS; TASK-004=IN_PROGRESS
Post-commit main/worktree status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
