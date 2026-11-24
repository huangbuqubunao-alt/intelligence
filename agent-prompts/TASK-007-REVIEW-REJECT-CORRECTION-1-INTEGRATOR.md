# TASK-007 第一轮审查拒绝 / Correction 1 — Status Integrator

## 身份与唯一目标

你是 **Status Integrator**，不是产品 Implementer、Reviewer 或 Product Integrator。唯一目标是把
TASK-007 的第一轮独立审查 `REJECT` 和已批准的 Correction 1 写入 `main` 控制面；不得运行产品
命令、修改任何 source worktree、合并、推送、清理、创建 Reviewer 或实现产品代码。

## 固定基线与隔离

- Main：`/Users/developer/Documents/youtubek agent`，分支 `main`，Required base：
  `8a2d74eb4b9794716149915da9876484e65d9b1f`。
- TASK-007 source：`/Users/developer/Documents/yia-worktrees/task-007`，分支
  `codex/task-007-local-scoring`，当前 review evidence：
  `266c488c17fc82cb648053b5e1066211a7bea9a9`；唯一父提交必须为
  `258358fcd5227e144c9294beafdf7ec6e2feea63`，review evidence 只能改
  `handoffs/TASK-007.md`。
- 不得读取、检查、修改、等待、清理或报告 TASK-006 source worktree。TASK-006 已在独立
  Correction 1 中，主线文件中的既有状态必须保持不变。
- 确认身份为 `Mozhu <maintainer@example.invalid>` 且 `user.useConfigOnly=true`；否则停止。

## 本包唯一允许的 main 文件

这些文件已经作为本包预置内容出现。只可暂存并提交这五个文件，不能把“初始工作树非空”当作
失败；其他路径出现变化立即停止，不自行清理。

1. `agent-prompts/TASK-007-REVIEW-REJECT-CORRECTION-1-INTEGRATOR.md`
2. `agent-prompts/TASK-007-CORRECTION-1-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-007-local-scoring.md`

## 本包的中断恢复例外（只适用于这一次）

此前一次提交尝试在完整门禁期间发现 `docs/PROJECT_STATUS.md` 的 working-tree 内容已修正，
但 index 仍保留更早的五文件版本，因而五个哈希不稳定并已正确停止。本段是主控对该**同一五文件**
状态的明确恢复授权，不增加文件范围或产品权限：

- 初始 index 可以已经包含且只能包含上述五个文件；initial working tree 也可以包含且只能包含
  上述五个文件。其他 staged、unstaged 或 untracked 路径出现即停止。
- 不得使用 `git reset`、`git restore`、`git checkout`、删除或清理。完成范围核对后，只能执行一次
  `git add --` 并精确列出上述五个路径，使 index 与当前工作区的已批准版本一致；这不是撤销并发
  内容，也不会触及范围外文件。
- **只有这次重新暂存完成后**才记录五个 SHA-256 并开始完整稳定性门禁。先前的
  `78a3b6...` / `26700a...` 哈希不得作为新一轮门禁基线。之后任一文件再变化立即停止，不得
  再次暂存或覆盖。

## 必须确认的内容

- `TASK-007` 从 `IN_REVIEW` 回到 `IN_PROGRESS`，负责人为原 Codex Implementer 的
  Correction 1；不得预写 `APPROVE`、`ACCEPTED`、`DONE`、merge SHA 或 Reviewer 结论。
- 审查 evidence `266c488c...` 是 `REJECT`，P1 恰为：完整异常链的响应泄漏/短读与畸形响应
  映射；未使用已有 SQLite Provider Call、Artifact、评分摘要与 `complete_stage` 原子完成。
- Correction scope 恰为：`scoring.py`、`providers/ollama.py`、两份既有评分测试、可选
  `tests/fixtures/scoring/**` 和 source handoff。禁止 `state.py`、Schema/migration、
  `domain.py`、配置、依赖、锁文件、真实 Ollama/模型/媒体/Vault 路径。
- TASK-006 状态为 `IN_PROGRESS` 的 Correction 1，授权和文字不得改变。

## 只读及提交门禁

1. 确认 main `HEAD` 精确等于 Required base，分支、身份、`user.useConfigOnly` 正确。按上节的
   中断恢复例外，核对 index 和 working tree 均只涉及上述五路径；然后一次性重新暂存这五路径。
   重新暂存后确认 `git diff --name-only` 无输出、cached scope 精确为五路径。
2. 重新暂存完成后记录五个 SHA-256；完整检查前后必须不变。
3. 核验 source branch/HEAD/父链/洁净度，以及 `6b4d59c...266c488c...` 全量 product Diff
   仍仅为原任务的 11 个允许文件；`pyproject.toml`/`uv.lock` 无差异；所有相关 Diff 的
   `git diff --check` 通过。
4. 对 main 运行 `git diff --check`、EOF/尾随空白检查；核对内容要求。不得运行 `uv`、pytest、
   build、数据库、模型、网络或任何 source 命令。
5. 只暂存上述五文件，运行 `git diff --cached --check`，确认 staged scope 精确。创建一个单父
   commit，建议消息：`docs: return TASK-007 for scoring correction`。
6. 提交后确认 main 干净、source 仍为 `266c488c...` 且干净，并确认动态授权：
   `git log -1 --format=%H -- agent-prompts/TASK-007-CORRECTION-1-CODEX.md` 解析到本次 main
   commit。

## 回传格式

```text
Task: TASK-007 first review reject / Correction 1 sync
Base / Head commit:
Committed files:
TASK-007 source / status:
Checks:
TASK-006 untouched:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
