# TASK-002 Closure and TASK-003/TASK-004 Readiness Sync

## 身份与边界

你是原 Status Integrator。本轮只提交 TASK-002 最终关闭和 TASK-003/TASK-004 就绪状态；不得运行产品代码、安装依赖、创建 worktree、分配 Implementer、修改产品实现、合并分支或清理现有 worktree。

## 固定基线

- Task: `TASK-002 status closure and TASK-003/TASK-004 readiness`
- Role: `Status Integrator`
- Required base: `main@823d68a2dffc1745e04cbbe54c817bf0c117a6fa`
- Main worktree: `/Users/hua/Documents/youtubek agent`
- TASK-002 source worktree: `/Users/hua/Documents/yia-worktrees/task-002`，严格只读
- Required source head: `d98de3537187ac346e404d7899d0a9d90c228483`
- Required merge parents: `e2aef7cd88f5c0f0f4e323a79234e71ca6a95845`、`d98de3537187ac346e404d7899d0a9d90c228483`

## 唯一允许提交的 7 个文件

- `agent-prompts/TASK-002-CLOSURE-AND-TASK-003-004-READINESS-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `handoffs/TASK-002.md`
- `tasks/README.md`
- `tasks/TASK-002-config-domain-contracts.md`
- `tasks/TASK-003-state-store.md`
- `tasks/TASK-004-discovery-metadata.md`

初始状态不是精确这 7 个文件、已有 staged 内容、main HEAD 不符、出现未解释的并发变化或 TASK-002 source worktree 不干净时，立即停止并报告；不得自行修文档或扩大范围。

## 必查事实

- main 当前 HEAD 精确为 merge commit `823d68a...`，其两个父提交顺序与本包一致。
- `d98de353...` 已是 main 的祖先；第一父到 merge commit 的文件范围精确为 TASK-002 批准的 8 个产品/证据文件。
- main 和 TASK-002 source worktree 都干净；source 分支仍为 `grok/task-002-config-domain-contracts`，不得删除或清理。
- Git 身份必须是 `Mozhu <huangbuqubunao@gmail.com>`，且 `user.useConfigOnly=true`。
- TASK-002 应关闭为 `DONE`，并记录 merge SHA、整合检查和 P3 剩余风险。
- TASK-003、TASK-004 的唯一依赖 TASK-002 已 `DONE`，任务级审批也已满足，因此两项均应为 `READY`、`UNASSIGNED`。
- 本轮不得把 TASK-003/TASK-004 设为 `IN_PROGRESS`，不得预先指定 Implementer/Reviewer，也不得创建它们的分支或 worktree。

## 只读检查

```bash
git branch --show-current
git rev-parse HEAD
git rev-list --parents -n 1 HEAD
git status --short
git config --get user.useConfigOnly
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
git merge-base --is-ancestor d98de3537187ac346e404d7899d0a9d90c228483 HEAD
git diff --name-status HEAD^1..HEAD
git -C "/Users/hua/Documents/yia-worktrees/task-002" branch --show-current
git -C "/Users/hua/Documents/yia-worktrees/task-002" rev-parse HEAD
git -C "/Users/hua/Documents/yia-worktrees/task-002" status --short
git diff --check
git diff --name-only
```

必须验证第一父差异精确为：

- `config/channels.example.yaml`
- `config/settings.example.yaml`
- `handoffs/TASK-002.md`
- `pyproject.toml`
- `src/youtube_intel/config.py`
- `src/youtube_intel/domain.py`
- `tests/unit/test_contracts.py`
- `uv.lock`

本轮不重跑产品测试；最终 Integrator 已在 merge 前完整重跑并报告通过。

## 内容核对

逐项确认：

- `docs/PROJECT_STATUS.md` 不再声称 TASK-002 尚未整合，当前并行调度与下一步一致。
- `tasks/README.md` 的项目门禁为 `TASK_003_004_READY`；表内 TASK-002=`DONE`、TASK-003/004=`READY`。
- `tasks/TASK-002-config-domain-contracts.md` 为 `DONE`，且 merge/source/review SHA 与检查记录准确。
- `handoffs/TASK-002.md` 的主控验收和整合结果已填写。
- `tasks/TASK-003-state-store.md`、`tasks/TASK-004-discovery-metadata.md` 只把状态改为 `READY`，Assignee 保持 `UNASSIGNED`，批准边界不变。
- TASK-004 的真实 YouTube 冒烟、Cookie、账号登录、remote components 和 ffmpeg 仍未授权。
- TASK-002 P3 风险继续保留：`MappingProxyType` 的私有 backing dict live view、写入时路径重检、运行时密钥解析职责。

## 暂存与提交

只暂存上述 7 个文件，然后运行：

```bash
git diff --cached --check
git diff --cached --name-only
git diff --cached
git status --short
```

暂存范围必须精确为 7 个文件，且不得有未暂存内容。提交消息：

```text
docs: close TASK-002 and ready TASK-003 TASK-004
```

提交后运行：

```bash
git status --short
git rev-parse HEAD
git rev-parse HEAD^
git diff --name-status 823d68a2dffc1745e04cbbe54c817bf0c117a6fa..HEAD
git log -1 --format='author=%an <%ae>%ncommitter=%cn <%ce>'
```

确认新提交是 `823d68a...` 的单父后继、范围精确为上述 7 个文件、main 干净且身份正确。不要继续创建 TASK-003/TASK-004 worktree；等待主控生成精确基线的并行分配包。

## 返回格式

```text
Task: TASK-002 closure and TASK-003/TASK-004 readiness
Role: Status Integrator
Base:
Head commit:
Git identity:
Checks:
Committed files:
Final states: TASK-002=DONE; TASK-003=READY/UNASSIGNED; TASK-004=READY/UNASSIGNED
Post-commit status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
