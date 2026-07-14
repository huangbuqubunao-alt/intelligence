# TASK-010：流程编排与恢复

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: TL / 实现 Agent
- Size: M
- Risk: High
- Depends on: TASK-003, TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009

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
