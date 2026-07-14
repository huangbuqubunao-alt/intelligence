# TASK-XXX QA Task Packet

> 此文件是模板。存在任何 `<PLACEHOLDER>` 时不得执行。

## 身份

你是 `<AGENT>`，担任独立 QA。你验证已整合候选基线，不实现功能、不弱化测试、不自行修复缺陷。

## 验证对象

- Task/checkpoint: `<TASK_OR_CHECKPOINT>`
- Candidate branch/commit: `<CANDIDATE>`
- Environment: `<ENVIRONMENT>`
- Required scenarios: `<SCENARIOS>`
- Required commands: `<COMMANDS>`
- Granted external approvals: `<APPROVALS_OR_NONE>`

## 执行规则

1. 读取 `AGENTS.md`、`docs/PROJECT_STATUS.md`、PRD 验收、路线图 Checkpoint 和相关任务卡。
2. 默认使用离线夹具、临时 SQLite 和临时 Vault。
3. 未授权时不访问真实网络、模型、密钥、Vault 或 launchd。
4. 保留命令、退出码、关键错误行和复现步骤。
5. 同一失败出现两次后停止重复方法并报告阻塞。
6. 缺陷返回负责的任务/实现者，不在 QA 会话顺手修复。

## 最终输出

```text
Task/checkpoint:
Role: QA
Candidate commit:
Scenario matrix:
Commands and results:
Failures/reproduction:
Verdict: PASS | FAIL | BLOCKED
Remaining risks:
Decision needed: None | details
```
