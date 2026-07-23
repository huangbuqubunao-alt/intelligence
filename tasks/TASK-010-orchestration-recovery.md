# TASK-010：流程编排与恢复

- Status: `IN_PROGRESS`
- Assignee: `Codex`
- Owner role: TL / 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009

## 2026-07-23 正式分配

- Base：`main@227bdeba3a4d9ddd57231b123bfdc4a2038af3d3`；Worktree：
  `/Users/hua/Documents/yia-worktrees/task-010`；Branch：`codex/task-010-orchestration-recovery`。
- Codex 为唯一 Implementer；完成后才分配全新独立 Reviewer。允许范围严格为本卡列出的
  Pipeline/Job/retry、两份集成测试与 handoff；不得修改领域/配置、`state.py`、Schema/migration、Provider、
  CLI、依赖/锁文件或任务状态。
- 只授权既有 Fake 与 pytest 临时 SQLite/文件探针。真实 Vault、用户笔记、网络、云端、凭据、媒体和模型继续禁止。

## 2026-07-23 实现证据与审查授权

- Implementation source：`e17d732db4cfb344ddd75ac8bc25990c216afc3f`，唯一父为固定 base
  `227bdeba3a4d9ddd57231b123bfdc4a2038af3d3`；完整 Diff 严格为本卡六个授权路径。
- Implementer 自报 focused `15`、全量 `397`、mypy、Ruff、CLI、lock/sync、offline build 与
  sdist/wheel migration/template inclusion 均 PASS；这些仅构成待独立复跑证据。
- 全新独立 Codex Reviewer 仅可向 source handoff 写审查证据，不得改业务代码、依赖、锁文件、main 或任务状态。

## 2026-07-23 第一轮独立审查拒绝与 Correction 1

- Reviewer evidence：`f929a2f114626f7f714134d0894b188548537e4e`，唯一父为 implementation
  `e17d732db4cfb344ddd75ac8bc25990c216afc3f`，只修改 source handoff。
- Verdict：`REJECT`，P1=1。真实 `RepositoryBackedAnalysisService` 成功返回 `AnalysisCompleted` 后，
  编排器未将结果映射为继续排程，导致没有 `NOTE_WRITE` Job，高价值视频停在 `ANALYSIS_READY`。
- 原 Implementer 只获 Correction 1：Pipeline 适配、两份既有集成测试和 handoff。必须以临时 SQLite 与真实
  repository-backed 服务返回路径证明成功分析创建唯一 NOTE_WRITE Job，且缓存恢复使用既有 Provider-call/Artifact
  身份与哈希验证；不得修改 `complete_stage`、Provider、Schema、依赖或真实资源边界。

## 目标

把已有切片接入统一 Pipeline 状态机，使单个视频能够从发现走到完成，并在阶段失败、进程中断和重复运行时保持幂等和可恢复。

## 范围

- 实现阶段处理器、Job 领取/租约、状态转换、重试退避和终态决策。
- 每阶段在执行前查询有效产物/调用缓存，执行后事务化登记产物和状态。
- 单个视频失败隔离，批次继续处理其他视频；支持从指定视频/失败阶段恢复。

## 范围外

- 不增加新的 Provider 或输出格式。
- 不实现定时调度安装或周报内容。
- 不通过捕获所有异常并标记成功来掩盖失败。

## 验收标准

- [ ] Fake Provider 集成测试覆盖高分、低分、无字幕、延后直播和不可用内容的完整状态路径。
- [ ] 在每个昂贵阶段“调用前、调用后落库前、落库后”注入中断，恢复后状态正确且可缓存调用不重复。
- [ ] 重试次数、退避、租约回收、失败隔离和 `JobStatus.FAILED_FINAL` 均符合 System Design；视频保留最近成功的 `PipelineStatus`，非法转换被拒绝。

## 验证

- [ ] `python -m pytest tests/integration/test_pipeline.py`
- [ ] `python -m pytest tests/integration/test_recovery.py`
- [ ] `mypy src && ruff check .`
- [ ] 人工检查：同一固定批次运行两次，记录数、调用数和笔记数均不增加。

## 预计触达文件

- `src/youtube_intel/pipeline.py`
- `src/youtube_intel/jobs.py`
- `src/youtube_intel/retry.py`
- `tests/integration/test_pipeline.py`
- `tests/integration/test_recovery.py`

## 交付证据

- 状态路径和故障注入矩阵。
- 两次重复运行的计数对比。
- 任何无法保证恰好一次的外部副作用及补偿策略。
