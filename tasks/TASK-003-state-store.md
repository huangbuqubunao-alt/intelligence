# TASK-003：SQLite 状态存储

- Status: `BLOCKED`
- Assignee: `UNASSIGNED`
- Owner role: 实现 Agent；TL 审批 Schema
- Size: M
- Risk: High
- Depends on: TASK-002
- Approval: `APPROVED` — 产品负责人已于 2026-07-14 批准 `ADR-003` S-01 至 S-08

## 目标

实现 SQLite 状态仓库，为视频、频道游标、Job、产物、Provider 调用缓存和周报提供事务化、可迁移、可恢复的持久化语义。

## 范围

- 按已审批 Schema 建立初始迁移和 Repository 接口实现。
- 实现视频 upsert、游标事务推进、阶段状态转换、Job 租约/回收、产物与调用缓存索引。
- 使用约束防止重复视频、重复活动 Job 和重复周报；使用逐次审计表保留自动尝试历史。
- 使用标准库 `sqlite3` 和受控 UTC 时钟，不新增数据库依赖。

## 范围外

- 不实现任何外部 Provider。
- 不保存字幕全文、云响应全文或密钥到 SQLite。
- 不添加破坏性自动迁移或数据库清理命令。

## 验收标准

- [ ] 新数据库可初始化，重复迁移幂等；Schema 版本/checksum 可查询，失败迁移不会留下半应用状态。
- [ ] 并发/重复 upsert、游标 CAS、Job 双领取/续租/过期回收和非法 Pipeline 转换均有集成测试。
- [ ] 数据库约束能阻止重复 `video_id`、含全局 scope 的重复活动 Job 和同周期重复报告。
- [ ] 每次自动尝试均可审计；阶段完成时状态、Artifact/Provider call 索引全有或全无提交。
- [ ] `uv build` 产出的 sdist/wheel 均包含 `migrations/001_initial.sql`，且不修改 `pyproject.toml`。

## 验证

- [ ] `uv run python -m pytest tests/integration/test_state_store.py`
- [ ] `uv run python -m pytest tests/unit/test_state_transitions.py`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv build`
- [ ] `git diff --check`
- [ ] 人工检查：中断一个 running Job，推进测试时钟后可重新领取且尝试历史仍可追踪。

## 预计触达文件

- `src/youtube_intel/state.py`
- `src/youtube_intel/migrations/001_initial.sql`
- `tests/integration/test_state_store.py`
- `tests/unit/test_state_transitions.py`
- `handoffs/TASK-003.md`

不得修改 `src/youtube_intel/domain.py`、Provider、编排、`pyproject.toml` 或 `uv.lock`。完整列、索引、事务和 Repository 语义以已接受的 `docs/decisions/ADR-003-sqlite-state-store-contract.md` 为准。

## 复用决定

- 直接复用 Python 标准库 `sqlite3`、`importlib.resources`、`datetime` 和现有领域对象，不引入 ORM、迁移框架或数据库依赖。
- 复用 SQLite 官方事务、约束和 PRAGMA 能力；本任务只实现项目特有的 Repository、幂等键和状态语义。
- 外部候选项目不拥有本项目的 Schema 或状态机；不得复制其数据库模型替代 ADR-003。

## 交付证据

- 产品负责人对 ADR-003 S-01 至 S-08 的审批记录（已满足）。
- 测试命令和关键约束场景结果。
- 迁移前后 Schema 版本/checksum 以及构建产物包含 SQL 的输出。
