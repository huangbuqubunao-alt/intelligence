# TASK-002 Assignment Sync — Status Integrator Packet

## 身份

你是原 `main` 控制面终端中的 Status Integrator。你只核对并提交主控已经准备好的 `TASK-002` worktree、角色和 `IN_PROGRESS` 分配状态，不修改内容、不安装依赖、不实现产品代码。

## 固定上下文

- Task: `TASK-002 assignment sync`
- Role: `Status Integrator`
- Target branch: `main`
- Repository: `/Users/developer/Documents/youtubek agent`
- Required base: `main@46f8497e771e1461034942dd7967f19d85f79f81`
- Implementer worktree: `/Users/developer/Documents/yia-worktrees/task-002`
- Implementer branch: `grok/task-002-config-domain-contracts`
- Suggested commit message: `docs: assign task 002 implementation`

开始前按顺序完整读取 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`tasks/README.md`、`tasks/TASK-002-config-domain-contracts.md` 和两个新任务包。任一文件冲突、基线不符或范围异常时立即停止，不自行修订内容。

## Expected files

初始 `git status --short` 必须只包含以下 6 个文件：

- `agent-prompts/PREFLIGHT-TASK-003-004-READONLY.md`
- `agent-prompts/TASK-002-ASSIGNMENT-INTEGRATOR.md`
- `agent-prompts/TASK-002-IMPLEMENTER-GROK.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-002-config-domain-contracts.md`

出现额外文件、并发写入或文件在检查期间变化，立即输出 `BLOCKED`；不得清理、覆盖、取消暂存或吸收其他人的修改。

## 必须确认的内容

1. `main` 精确位于 `46f8497e771e1461034942dd7967f19d85f79f81`，初始范围只有 6 个 Expected files。
2. `/Users/developer/Documents/yia-worktrees/task-002` 存在、干净，分支为 `grok/task-002-config-domain-contracts`，HEAD 精确为 `46f8497e771e1461034942dd7967f19d85f79f81`。
3. `TASK-002` 为 `IN_PROGRESS`，Grok 是唯一 Implementer；Codex Reviewer 明确等待实现 commit。
4. Implementer 包无占位符，绑定正确 base/worktree/branch，允许范围精确为任务卡 8 个文件。
5. 依赖与权限仍精确为已批准范围；没有新增 extras、依赖、真实密钥/Vault、云调用、数据库 Schema 或 launchd 权限。
6. `PREFLIGHT-TASK-003-004-READONLY.md` 明确只在 `main`、只读、状态同步提交后运行，不构成后续任务实现授权。
7. `TASK-003`、`TASK-004` 及后续写入型任务仍保持 `BLOCKED`。

## 执行步骤

1. 运行并核对：

   ```bash
   pwd
   git branch --show-current
   git rev-parse HEAD
   git status --short
   git -C /Users/developer/Documents/yia-worktrees/task-002 branch --show-current
   git -C /Users/developer/Documents/yia-worktrees/task-002 rev-parse HEAD
   git -C /Users/developer/Documents/yia-worktrees/task-002 status --short
   ```

2. 运行：

   ```bash
   git diff --check
   git diff --name-status
   ```

   完整读取并核对 6 个 Expected files；不得编辑。

3. 仅暂存 Expected files：

   ```bash
   git add agent-prompts/PREFLIGHT-TASK-003-004-READONLY.md agent-prompts/TASK-002-ASSIGNMENT-INTEGRATOR.md agent-prompts/TASK-002-IMPLEMENTER-GROK.md docs/PROJECT_STATUS.md tasks/README.md tasks/TASK-002-config-domain-contracts.md
   ```

4. 确认暂存范围与内容：

   ```bash
   git diff --cached --check
   git diff --cached --name-status
   git diff --cached
   git diff --name-only
   git status --short
   ```

   `git diff --name-only` 必须无输出；`git status --short` 必须只显示 6 个 Expected files 且均已暂存。

5. 创建一个 commit：

   ```bash
   git commit -m "docs: assign task 002 implementation"
   ```

6. 提交后运行：

   ```bash
   git status --short
   git rev-parse HEAD
   git -C /Users/developer/Documents/yia-worktrees/task-002 status --short
   git -C /Users/developer/Documents/yia-worktrees/task-002 rev-parse HEAD
   ```

   `main` 必须干净；TASK-002 worktree 必须仍干净且保持原 base。不要运行 Implementer、安装依赖、改变实现分支或把后续任务设为 `READY`。

## 最终输出

```text
Task: TASK-002 assignment sync
Role: Status Integrator
Base: main@46f8497e771e1461034942dd7967f19d85f79f81
Head commit:
Checks:
- Initial and staged scope:
- TASK-002 status/roles:
- Worktree/branch/base/clean:
- Implementer packet:
- Read-only preflight packet:
- TASK-003/TASK-004 states:
- git diff --check:
- git diff --cached --check:
- Post-commit statuses:
Committed files:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
