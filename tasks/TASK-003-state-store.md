# TASK-003：SQLite 状态存储

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: 实现 Agent；TL 审批 Schema
- Size: M
- Risk: High
- Depends on: TASK-002
- Approval required: 最终 SQLite Schema 和迁移策略

## 目标

实现 SQLite 状态仓库，为视频、频道游标、Job、产物、Provider 调用缓存和周报提供事务化、可迁移、可恢复的持久化语义。

## 范围

- 按已审批 Schema 建立初始迁移和 Repository 接口实现。
- 实现视频 upsert、游标事务推进、阶段状态转换、Job 租约/回收、产物与调用缓存索引。
- 使用约束防止重复视频、重复活动 Job 和重复周报。

## 范围外

- 不实现任何外部 Provider。
- 不保存字幕全文、云响应全文或密钥到 SQLite。
- 不添加破坏性自动迁移或数据库清理命令。

## 验收标准

- [ ] 新数据库可初始化，重复迁移幂等；Schema 版本可查询，迁移失败不会留下半应用状态。
- [ ] 并发/重复 upsert、Job 租约过期回收和非法状态转换均有集成测试。
- [ ] 数据库约束能阻止重复 `video_id`、重复活动 Job 和同周期重复报告。

## 验证

- [ ] `python -m pytest tests/integration/test_state_store.py`
- [ ] `python -m pytest tests/unit/test_state_transitions.py`
- [ ] `mypy src && ruff check .`
- [ ] 人工检查：中断一个 running Job，推进测试时钟后可重新领取且尝试历史仍可追踪。

## 预计触达文件

- `src/youtube_intel/state.py`
- `src/youtube_intel/migrations/001_initial.sql`
- `tests/integration/test_state_store.py`
- `tests/unit/test_state_transitions.py`

## 交付证据

- TL 的 Schema 审批记录。
- 测试命令和关键约束场景结果。
- 迁移前后 Schema 版本输出。
