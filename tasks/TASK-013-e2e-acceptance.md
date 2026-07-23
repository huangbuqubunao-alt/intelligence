# TASK-013：端到端验收

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: QA Agent
- Size: M
- Risk: High
- Depends on: TASK-011, TASK-012
- Approval required: 真实网络、真实频道、本地模型、云端模型或真实 Vault 冒烟均需按范围授权

## 目标

用可重复的离线夹具证明完整 MVP 行为，并在用户批准后执行最小真实环境冒烟，形成 PRD 验收矩阵和发布决策证据。

## 范围

- 建立 5 类固定场景：人工字幕、自动字幕、无字幕/Whisper、低分、高分。
- 对字幕、转写、评分、云分析、笔记写入逐阶段做失败注入和恢复验证。
- 执行重复运行、云关闭、秘密扫描、笔记用户区保留和周报幂等检查。

## 范围外

- 不通过修改实现、删除断言或跳过失败用例来完成验收。
- 不扩大到 V2 数据源、性能压测或多用户测试。
- 未获授权不接触用户真实 Vault 或付费云模型。

## 验收标准

- [ ] `docs/PRD.md` 第 10 节每一条验收标准都有测试/人工证据和通过/失败状态。
- [ ] 离线端到端套件默认无网络、无真实密钥、无真实 Vault 也能通过，并验证重复运行无重复副作用。
- [ ] 经授权的真实冒烟（或明确记录未授权）有命令、环境、脱敏结果、清理方式和剩余风险。

## 验证

- [ ] `python -m pytest tests/e2e -m 'not network and not cloud'`
- [ ] `python -m pytest`
- [ ] `ruff check . && mypy src`
- [ ] `git diff --check && git status --short`
- [ ] 人工验收：临时 Vault 中核对 5 个场景和对应周报。

## 预计触达文件

- `tests/e2e/test_mvp_flow.py`
- `tests/e2e/test_failure_recovery.py`
- `tests/e2e/fixtures/` 下最小合法夹具集
- `docs/ACCEPTANCE_REPORT.md`
- 测试配置文件（仅在必要且已审批时）

## 失败处理

若同一失败连续出现两次，停止重复同一方案，在验收报告中保留：命令、关键错误行、受影响文件、两次已尝试方法和建议负责人。

## 交付证据

- 完整验收矩阵。
- 全部质量命令结果。
- 真实冒烟授权/未执行声明和剩余风险。

## 只读预检授权（2026-07-23）

- 产品负责人只授权 Codex Scout 在 main 上梳理离线验收覆盖、用户可见结果、资源边界与后续决策；不授权代码、夹具、验收报告、worktree 或测试命令写入。
- 预检必须将 PRD 第 10 节的离线可证实结果、待端到端连接验证结果和需单独批准的真实冒烟明确分开。
- 任务仍为 `BLOCKED/UNASSIGNED`；预检结论不能替代实现、真实频道/模型/Vault、密钥或付费调用授权。
