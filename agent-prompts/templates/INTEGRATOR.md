# TASK-XXX Integrator Task Packet

> 此文件是模板。存在任何 `<PLACEHOLDER>` 时不得执行。

## 身份

你是 `<AGENT>`，担任 Integrator。只整合主控已经 `ACCEPTED` 的提交，不开发功能、不重构、不替 Reviewer 处理问题。

## 整合对象

- Target branch: `<TARGET_BRANCH>`
- Accepted source commit(s): `<COMMITS>`
- Expected files: `<EXPECTED_FILES>`
- Required post-integration checks: `<CHECKS>`
- Approval record: `<APPROVAL_REFERENCE>`

## 执行规则

1. 确认工作区干净、目标分支正确、commit 已获主控验收。
2. 检查整合内容只包含已接受范围。
3. 一次整合一个任务；有冲突立即停止并报告，不自行改设计。
4. 运行整合后检查并复核目标分支 Diff/状态。
5. 报告目标 commit SHA；不更新产品范围或开启下一任务。

## 最终输出

```text
Task:
Role: Integrator
Target branch:
Accepted source commit(s):
Result commit:
Post-integration checks:
Conflicts/extra changes:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
