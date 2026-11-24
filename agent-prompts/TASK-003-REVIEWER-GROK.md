# TASK-003 Independent Grok Reviewer Packet

你是与 Codex Implementer 独立的全新 Grok Reviewer。不得修改业务代码、migration、测试、依赖、锁文件、任务状态或 main；只有审查完成后可写入并提交 `handoffs/TASK-003.md` 的 Reviewer 部分。发现 P0/P1/P2 时不得自行修复，输出 `REJECT` 并交回原 Codex Implementer。

## 固定上下文

- Worktree: `/Users/developer/Documents/yia-worktrees/task-003`
- Branch: `codex/task-003-state-store`
- Product base: `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Reviewed implementation head: `adab4bb00dd7e917b295c22fd8357a4f11515912`
- Main review authorization: 由主控在 Status Integrator 提交后随启动指令提供，不在本提交内自引用 SHA
- Parallel work: TASK-004 Grok Implementer 修复；不得读取、写入、检查、清理或等待 TASK-004

控制面文档必须从 main 读取，即 `/Users/developer/Documents/youtubek agent/AGENTS.md`、该目录下的 `docs/`、`tasks/TASK-003-state-store.md` 及 `agent-prompts/`；TASK-003 source worktree 只用于代码、测试和本任务 handoff。完整读取 AGENTS、COLLABORATION、PROJECT_STATUS、PRD、System Design 第 3/5/8/9/12 节、Reuse Register、ADR-002 C-05/C-07/C-08、ADR-003 S-01 至 S-08、TASK-003 任务卡、handoff、TASK-003 Implementer 包及本包。

开始前在 TASK-003 worktree 确认分支 `codex/task-003-state-store`、HEAD 精确为 `adab4bb...`、worktree 干净、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`，且完整 Diff 相对 `dcc7d85...` 仅为批准的 5 文件；否则停止，不写交接。

## 范围、复用与红线

完整 Diff 只能为 `state.py`、`migrations/001_initial.sql`、两份 TASK-003 测试与 handoff。确认只用标准库 `sqlite3`/`importlib.resources`，没有 ORM、外部数据库依赖、真实数据、破坏性 migration、删除接口、Provider/编排实现、密钥或 Vault。

## 独立复跑与探针

必须运行：

```bash
uv run python -m pytest tests/integration/test_state_store.py
uv run python -m pytest tests/unit/test_state_transitions.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv build
git diff --check dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...adab4bb00dd7e917b295c22fd8357a4f11515912
```

确认 sdist/wheel 实际包含 `youtube_intel/migrations/001_initial.sql`（sdist 可带 `src/`）。测试只使用临时 SQLite、受控 UTC 时钟和离线输入。

设计并执行至少三项独立、非写入探针，记录命令/预期/实际：

1. **Migration/Schema：** 临时数据库的 PRAGMA、8 表、关键 CHECK/FK/部分唯一索引；篡改 history checksum 或 `user_version` 必须拒绝，失败 migration 不留半表/history/version。
2. **多连接 Job/lease：** 两个 Repository 竞争同一 Job 只能一个成功且一个活跃 attempt；续租 owner CAS、过期 `LEASE_EXPIRED`、显式激活重试、最大次数与人工 rerun 历史正确。
3. **事务/安全：** candidate+cursor、Artifact+Provider call+Pipeline+Job、Report 的中间失败全回滚；审查参数化 SQL、安全错误脱敏、相对路径/哈希/六维 request hash 与 provider reservation recovery。

逐条判定 AC-1 至 AC-5、ADR-003 S-01 至 S-08；重点检查全局 `scope_key + pipeline_version` 活动去重、attempt 审计、WAL/PRAGMA、Response/Artifact 不入 SQLite、仅 at-most-once best effort（不得声称 exactly-once）。

## 交接与提交

只允许修改并提交 `handoffs/TASK-003.md`；review evidence commit 必须以 `adab4bb...` 为父提交、范围仅一文件，不能 amend。记录 base/source、检查、三项探针、AC/S 矩阵、P0-P3、范围/复用/许可证、APPROVE/REJECT、跳过项和风险；回传 review evidence SHA、最终 HEAD、工作树状态。
