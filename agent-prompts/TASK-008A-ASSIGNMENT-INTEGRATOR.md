# TASK-008A assignment — Worktree / Status Integrator

你是全新的 Codex Worktree / Status Integrator。你只创建已批准的 TASK-008A
worktree，并提交主控已经准备好的控制面文件。不得实现产品代码、运行 `uv`、测试、
构建、imports、数据库、OpenAI、token-count、网络、密钥、Vault、媒体或其他真实
资源命令。

## 固定授权

- Main repository：`/Users/hua/Documents/youtubek agent`
- Required main base：`82d1fd7c7f2f82e77df0518e63755bad0bf240f2`
- Worktree：`/Users/hua/Documents/yia-worktrees/task-008a`
- Branch：`codex/task-008a-cloud-analysis-shared-contracts`
- Implementer：Codex
- Reviewer：实现 commit 完成后启动全新独立 Codex 会话
- Required identity：`Mozhu <huangbuqubunao@gmail.com>`；
  `user.useConfigOnly=true`

产品负责人已批准 ADR-008 A-01 至 A-15，以及 TASK-008A 使用
`openai>=2.46.0,<2.47`、`tiktoken>=0.13.0,<0.14`、必要传递依赖、网络包下载、
`pyproject.toml`/`uv.lock` 修改和任务卡离线验证/构建。本分配只创建 worktree 和
提交控制面，不执行上述产品动作。

真实 OpenAI API、环境变量值/密钥、付费调用、云端 token-count、真实 Vault/用户
内容、最终文件删除/移动/重命名，以及 Schema/migration/`state.py`/
`complete_stage` 修改仍未授权。

## 开始门禁

开始时必须满足：

- main 分支和 HEAD 精确为 Required main base；
- 身份和 `user.useConfigOnly` 精确匹配；
- 暂存区为空；
- main 工作区恰有下列 6 个主控准备的 Markdown 文件，且没有其他修改或未跟踪路径；
- 目标 worktree 路径和 branch 均不存在。

任一条件不符立即 `BLOCKED`。不得 stash、reset、restore、checkout、merge、rebase、
cherry-pick、pull、覆盖、删除、清理或自行选择其他 SHA。

## 唯一允许提交的 main 文件

1. `agent-prompts/TASK-008A-ASSIGNMENT-INTEGRATOR.md`
2. `agent-prompts/TASK-008A-IMPLEMENTER-CODEX.md`
3. `docs/PRODUCT_DECISIONS.md`
4. `docs/PROJECT_STATUS.md`
5. `tasks/README.md`
6. `tasks/TASK-008A-cloud-analysis-shared-contracts.md`

## 执行步骤

1. 完整读取 `AGENTS.md`、`docs/COLLABORATION.md`、TASK-008A、本包和 Implementer
   包。验证 main base、身份、空 index、精确 6 文件准备范围、目标 branch/path
   不存在，并记录 6 文件 SHA-256。
2. 从 Required main base 创建指定 worktree/branch；确认 source branch/HEAD
   精确为 base 且工作区干净。不得在 source 中写文件或运行产品命令。
3. 再次核验 main 6 文件范围和哈希未变化，完整 Diff 内容一致，LF at EOF、尾随
   空白与 `git diff --check` 通过。
4. 只暂存上述 6 文件，比较 staged blob SHA-256，运行
   `git diff --cached --check`，确认暂存范围精确且没有未暂存内容。
5. 创建单一非 merge commit：

```text
docs: assign TASK-008A cloud contract worktree
```

6. 提交后确认唯一父提交为 Required main base；本包和 Implementer 包均动态解析到
   新提交；main 干净，source 仍在 base 且干净。

## 必须确认的控制面

- TASK-008A=`IN_PROGRESS`；Codex 为唯一 Implementer；全新独立 Codex Reviewer
  只等待实现 commit，本轮不启动。
- source 快照仍显示分配前的 `READY/UNASSIGNED` 是预期行为；实时分配事实以 main
  新控制面提交为准，Implementer 包必须明确处理这一差异。
- source 完整产品 Diff 只能包含：
  `src/youtube_intel/domain.py`、`src/youtube_intel/config.py`、
  `config/settings.example.yaml`、`tests/unit/test_contracts.py`、
  `pyproject.toml`、`uv.lock`、`handoffs/TASK-008A.md`。
- TASK-009A/TASK-008/TASK-009 均保持 `BLOCKED/UNASSIGNED`；不得创建其 worktree。
- 不新增 Schema/migration，不修改 `state.py`、`complete_stage`、Provider、CLI、
  Prompt 或产品编排。
- 本轮不安装依赖、不运行测试/构建、不修改 source/handoff、不启动 Worker、不
  merge/push/cleanup。

## 报告格式

```text
Task: TASK-008A assignment sync
Role: Worktree / Status Integrator
Base: main@...
Head commit: ... | None
Worktree/branch/base: ...
Git identity: ...
Committed files: ...
Checks: ...
TASK-008A/TASK-009A/TASK-008/TASK-009 gates: ...
Post-commit main/source status: ...
Verdict: INTEGRATED | BLOCKED
Remaining risks: ...
```
