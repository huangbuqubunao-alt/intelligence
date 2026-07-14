# TASK-XXX Reviewer Task Packet

> 此文件是模板。存在任何 `<PLACEHOLDER>` 时不得执行。

## 身份

你是 `<AGENT>`，担任 `TASK-XXX` 的独立 Reviewer。实现者为 `<IMPLEMENTER>`。只审查，不修改业务代码；只可补充 `handoffs/TASK-XXX.md` 的 Reviewer 部分。

## 固定上下文

读取 `AGENTS.md`、`docs/PROJECT_STATUS.md`、相关 PRD/System Design 章节、任务卡和已有交接报告。不要依赖实现者的结论替代实际检查。

## 审查对象

- Base: `<BASE_BRANCH>@<BASE_COMMIT>`
- Branch: `<BRANCH>`
- Reviewed commit: `<HEAD_COMMIT>`
- Worktree: `<ABSOLUTE_WORKTREE_PATH>`
- Required checks: `<REQUIRED_CHECKS>`
- Review focus: `<TASK_SPECIFIC_FOCUS>`

## 审查规则

1. 确认 commit 与交接报告一致。
2. 审查 `base...HEAD` 完整 Diff 和所有新增文件。
3. 逐条验证任务验收条件，重新运行关键检查。
4. 优先发现正确性、回归、状态/异常、测试遗漏、安全、红线和范围外修改。
5. 以 P0/P1/P2/P3 输出可操作问题，包含文件和行号。
6. 有问题时给出 `REJECT`，退回原 Implementer；不要代替其修复。
7. 无问题时也列出实际检查证据和剩余风险，不能只写“看起来可以”。

## 最终输出

```text
Task: TASK-XXX
Role: Reviewer
Reviewed commit:
Checks rerun:
Findings: P0/P1/P2/P3 with file references
Acceptance matrix:
Scope/red-line review:
Verdict: APPROVE | REJECT
Remaining risks:
Decision needed: None | details
```
