# TASK-013：端到端验收

- Status: `IN_PROGRESS`
- Assignee: `Codex Implementer`
- Owner role: QA Agent
- Size: M
- Risk: High
- Depends on: TASK-011, TASK-012, TASK-013A
- Approval required: 真实网络、真实频道、本地模型、云端模型或真实 Vault 冒烟均需按范围授权

## 重新分配（2026-07-26）

- Worktree: `/Users/hua/Documents/yia-worktrees/task-013-rebuild`
- Branch: `codex/task-013-e2e-acceptance-rebuild`
- Base: `main@2a59dfe3860161a5989f2c08161f03c73aa4ca86`
- TASK-013A 已整合为 `DONE`。本轮必须通过现有 `SubtitleAcquisitionService`、`LocalTranscriptionService`、评分、分析、笔记和周报服务建立真实离线服务流证据；不得重用已拒绝的历史 `codex/task-013-e2e-acceptance` source 或以通用 handler/直接状态推进替代。
- 完成后必须由全新独立 Codex Reviewer 审查；不得预写 verdict、ACCEPTED、merge 或 DONE。

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
- 预检执行时任务仍为 `BLOCKED/UNASSIGNED`；预检结论本身不能替代实现、真实频道/模型/Vault、密钥或付费调用授权。

## 离线实施授权（2026-07-23）

- 产品负责人批准只用测试内组合现有服务、固定夹具和 pytest 临时 SQLite/data/Vault 目录，补齐五个用户情形、失败恢复、重跑幂等和验收报告。
- 允许范围严格为两份 `tests/e2e` 测试、其 fixtures、`docs/ACCEPTANCE_REPORT.md` 和 `handoffs/TASK-013.md`；不改生产 CLI/编排、配置、Schema/migration、依赖、锁文件、测试配置或既有测试。
- 真实频道/YouTube、Whisper/ffmpeg、Ollama/模型、OpenAI/API/密钥/付费调用、真实 Vault/用户笔记、网络、媒体和 launchd 继续不授权。
- 真实冒烟在验收报告中只能写为 `NOT AUTHORIZED`；离线服务组合证据不能表述为真实 Provider 或真实 CLI 冒烟已经完成。

## 审查授权（2026-07-23）

- 实现提交 `fd22c8ced0343a38e4cb8acdde0ef608bc6d8708` 仅包含两份端到端测试、固定 fixtures、验收报告和 handoff；主控已授权全新独立 Codex Reviewer 复跑离线门禁和产品覆盖探针。
- 审查前不得把实现者自报的 6 个离线 E2E、427 个全量测试或 `PASS` 表述为最终验收；Reviewer 只可写 source handoff，不能修正业务或测试代码。

## 首轮审查退回与 Correction 1（2026-07-24）

- 独立 Reviewer evidence `2afd95a8dde9ae2d907480fd190bcb2c54efccb4` 的 Verdict 为 `REJECT`：现有 E2E 通过通用 handler 直接推进 SQLite 状态，不能证明五种用户路径、分阶段恢复或昂贵步骤缓存；PRD 10.7 也缺可复现的秘密扫描证据。
- Correction 1 仍严格限于既有两份 E2E 测试、fixtures、验收报告和 handoff。必须以现有服务边界与固定 Fake Adapter 形成测试内 composition，不得为测试修改生产 CLI 或接触真实资源。

## TASK-013A 依赖（2026-07-24）

- 产品负责人批准 ADR-012 的生产级方案：无字幕后的本地 Whisper 转写必须作为正式、可恢复的 TRANSCRIPT 阶段能力持久化，才能继续进入评分、分析、笔记与周报。
- 该能力不应藏在验收测试内；TASK-013 因此保持 `BLOCKED/UNASSIGNED`，等待 TASK-013A 整合后以真实服务路径重新实施离线验收。
