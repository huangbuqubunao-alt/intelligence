# TASK-002 Final Product Integrator Packet

## 身份

你是 `TASK-002` 的最终 Integrator。你只整合已被 Reviewer 和主控接受的 source head，不实现、修复、重构或重新设计产品代码，不改变公共任务状态，不清理分支/worktree，不推送远程。

## 开工包

- Task: `TASK-002`
- Role: `Integrator`
- Agent: 原 Integrator 会话
- Acceptance anchor: `main@1d8d16115173297aecb04a1a2ecfc2dc2927e3ff`
- Required execution base: main 当前干净 HEAD，且必须是 anchor 的单父后继、相对 anchor 只新增本文件与 `TASK-002-INTEGRATOR-PACKET-SYNC.md`
- Main worktree: `/Users/hua/Documents/youtubek agent`
- Source worktree: `/Users/hua/Documents/yia-worktrees/task-002`，只读
- Source branch: `grok/task-002-config-domain-contracts`
- Accepted source/review head: `d98de3537187ac346e404d7899d0a9d90c228483`
- Reviewed implementation source: `8f50df2f7e93d778f32947ca471740b6713c9aff`
- Review verdict: `APPROVE`
- Current task status: `ACCEPTED`
- Reuse decision: `DIRECT` 使用已批准 Pydantic/PyYAML；无额外复用或依赖
- Waiting after merge: 主控状态关闭；TASK-003/TASK-004 继续等待 `DONE`

## 预检

完整读取 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`tasks/TASK-002-config-domain-contracts.md`、`handoffs/TASK-002.md`（从 source 查看）和本包。

在 main 运行：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git rev-parse HEAD^
git status --short
git config --get user.useConfigOnly
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
git diff --name-status 1d8d16115173297aecb04a1a2ecfc2dc2927e3ff..HEAD
```

必须同时满足：

- 当前分支为 `main`，工作树无 staged/unstaged/untracked 文件。
- `HEAD^` 精确等于 acceptance anchor `1d8d161...`。
- anchor...HEAD 只新增：
  - `agent-prompts/TASK-002-INTEGRATOR-PACKET-SYNC.md`
  - `agent-prompts/TASK-002-INTEGRATOR.md`
- `user.useConfigOnly=true`，Author/Committer 非空且不含 `.local`。
- `tasks/TASK-002-config-domain-contracts.md` 为 `ACCEPTED`，不是 `DONE`。

在 source worktree 只读确认：

```bash
git -C "/Users/hua/Documents/yia-worktrees/task-002" branch --show-current
git -C "/Users/hua/Documents/yia-worktrees/task-002" rev-parse HEAD
git -C "/Users/hua/Documents/yia-worktrees/task-002" status --short
git -C "/Users/hua/Documents/yia-worktrees/task-002" rev-list --parents -n 1 d98de3537187ac346e404d7899d0a9d90c228483
git -C "/Users/hua/Documents/yia-worktrees/task-002" diff --name-status 8f50df2f7e93d778f32947ca471740b6713c9aff..d98de3537187ac346e404d7899d0a9d90c228483
git -C "/Users/hua/Documents/yia-worktrees/task-002" diff --check 46f8497e771e1461034942dd7967f19d85f79f81...d98de3537187ac346e404d7899d0a9d90c228483
```

source 必须为指定分支与 HEAD、工作树干净；review commit 的父提交为 `8f50df2...` 且只修改 `handoffs/TASK-002.md`。

## 允许进入 main 的 source 文件

合并 source 后，相对 merge 第一父提交的内容范围必须恰好为：

- `config/channels.example.yaml`
- `config/settings.example.yaml`
- `handoffs/TASK-002.md`
- `pyproject.toml`
- `src/youtube_intel/config.py`
- `src/youtube_intel/domain.py`
- `tests/unit/test_contracts.py`
- `uv.lock`

不得顺便修改任务状态、提示词、其他文档、依赖范围或任何第九个文件。

## 合并与门禁

1. 记录实际执行 base SHA，然后在 main 执行：

   ```bash
   git merge --no-ff --no-commit d98de3537187ac346e404d7899d0a9d90c228483
   ```

2. 有冲突时不得解决或编辑。记录冲突文件，执行 `git merge --abort`，确认返回原执行 base 且干净，然后报告 `BLOCKED`。
3. 无冲突时检查：

   ```bash
   git diff --cached --check
   git diff --cached --name-status
   git status --short
   ```

   暂存范围必须精确为批准 8 文件；无其他未暂存或未跟踪文件。不要修改已合并内容。

4. 在未提交 merge 状态运行全部整合门禁：

   ```bash
   uv lock --check
   uv sync --locked
   uv run python -m pytest tests/unit/test_contracts.py
   uv run python -m pytest
   uv run mypy src
   uv run ruff check .
   uv run python -m youtube_intel --help
   git diff --cached --check
   ```

   仅允许出现被 `.gitignore` 正确忽略的环境、缓存和构建产物。若授权依赖因网络沙箱失败，可按 TASK-002 已批准范围请求权限后原命令重跑；不得改锁文件、删减测试或放宽门禁。

5. 任一门禁失败：记录命令、关键错误和已运行结果；不得修代码。执行 `git merge --abort`，确认回到执行 base 且干净，报告 `BLOCKED`。
6. 全部通过后创建显式 merge commit：

   ```bash
   git commit -m "merge: integrate TASK-002 configuration contracts"
   ```

## 提交后验证

```bash
git rev-parse HEAD
git rev-list --parents -n 1 HEAD
git merge-base --is-ancestor d98de3537187ac346e404d7899d0a9d90c228483 HEAD
git diff --name-status HEAD^1..HEAD
git status --short
git log -1 --format='author=%an <%ae>%ncommitter=%cn <%ce>'
```

必须证明：

- merge commit 恰有两个父提交：第一父为本轮实际执行 base，第二父为 `d98de353...`。
- source head 已成为 main 祖先。
- 第一父到 merge commit 的文件范围恰好为批准 8 文件。
- main 干净，Author/Committer 使用已配置身份且不含 `.local`。
- TASK-002 仍为 `ACCEPTED`；不得在本轮改为 `DONE`。
- source branch 与 worktree 保留，不删除、不清理。

## 返回格式

```text
Task: TASK-002
Role: Integrator
Acceptance anchor:
Execution base:
Source head:
Merge commit:
Merge parents:
Pre-merge scope:
Checks: command + result
Post-merge task status:
Post-merge main/source worktree status:
Git author/committer identity:
Unexpected files:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
