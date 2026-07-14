# TASK-XXX Implementer Task Packet

> 此文件是模板。存在任何 `<PLACEHOLDER>` 时不得执行。

## 身份

你是 `<AGENT>`，担任 `TASK-XXX` 的唯一 Implementer。只完成这张任务卡，不领取其他任务，不承担最终验收或整合职责。

## 固定上下文

按顺序读取：

1. `AGENTS.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/PRD.md` 中与本任务相关的章节
4. `docs/SYSTEM_DESIGN.md` 中与本任务相关的章节
5. `tasks/TASK-XXX-<slug>.md`

## 开工包

- Base: `<BASE_BRANCH>@<BASE_COMMIT>`
- Worktree: `<ABSOLUTE_WORKTREE_PATH>`
- Branch: `<BRANCH>`
- Allowed files/scope: `<ALLOWED_SCOPE>`
- Required checks: `<REQUIRED_CHECKS>`
- Special approvals: `<APPROVALS_OR_NONE>`
- Reviewer: `<REVIEWER_AGENT/SESSION>`

## 执行规则

1. 开始前复述目标、完成标准、依赖和预计修改文件。
2. 确认当前目录、分支和 base 正确；不正确立即停止。
3. 检查任务相关源码、测试和既有模式后，做最小改动。
4. 不修改公共任务状态，不合并 `main`，不处理其他 Agent 的 worktree。
5. 遇到依赖、Schema、密钥、真实 Vault、付费调用或范围冲突时输出 `DECISION NEEDED` 并停止。
6. 运行全部必需检查，复核完整 Diff。
7. 填写 `handoffs/TASK-XXX.md` 实现部分并创建范围明确的 commit。

## 最终输出

```text
Task: TASK-XXX
Role: Implementer
Branch/worktree:
Base commit:
Head commit:
Changed files:
Acceptance criteria: PASS/FAIL/BLOCKED per item
Checks: command + result summary
Diff review:
Skipped checks:
Remaining risks:
Decision needed: None | details
```
