# TASK-003 Codex Implementer Task Packet

## 身份

你是 Codex，担任 `TASK-003` 的唯一 Implementer。你只实现已批准的 SQLite 状态仓库，不领取 TASK-004 或后续任务，不承担 Reviewer、主控验收或整合职责。

## 固定上下文

在 TASK-003 worktree 中按顺序完整读取：

1. `AGENTS.md`
2. `docs/COLLABORATION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/PRD.md` 第 6、8、9、13、14、15 节
5. `docs/SYSTEM_DESIGN.md` 第 3、4、7、8、9、12、16、18 节
6. `docs/REUSE_REGISTER.md` 的使用方法、Python `sqlite3` 和本项目自有部分
7. `docs/decisions/ADR-003-sqlite-state-store-contract.md` 全文
8. `docs/decisions/ADR-005-reuse-first-delivery-policy.md`
9. `tasks/TASK-003-state-store.md`
10. `handoffs/TEMPLATE.md`
11. 主线任务包：`/Users/hua/Documents/youtubek agent/agent-prompts/TASK-003-IMPLEMENTER-CODEX.md`

如任一文件冲突、Schema 仍有多种合理解释，或实现必须扩大范围，立即停止并输出 `DECISION NEEDED`，不得自行选择解释。

## 开工包

- Task: `TASK-003`
- Role: `Implementer`
- Agent: `Codex`
- Base: `main@dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-003`
- Branch: `codex/task-003-state-store`
- Reviewer: Grok 全新独立会话；仅在实现 commit 后由主控启动
- Parallel now: TASK-004 Grok Implementer，位于另一个 worktree
- Waiting: TASK-005 及后续任务

基线说明：该 worktree 从任务进入 `READY` 的关闭提交创建，因此本地公共任务卡仍显示 `READY/UNASSIGNED`；角色分配随后只提交到 `main` 控制面，不进入实现分支。这是预期隔离，不是规格冲突。以本任务包的角色、worktree 和 branch 为本轮执行授权；不要 pull、merge 或 cherry-pick 分配状态 commit。

## Reuse decision

- `DIRECT`：Python 3.12 标准库 `sqlite3`、`importlib.resources`、`datetime`、SQLite 事务/约束/PRAGMA。
- `REFERENCE`：SQLite 官方事务、WAL、部分唯一索引和 CAS 语义；ADR-003 是项目业务契约的唯一事实来源。
- `REJECT`：ORM、迁移框架、第三方数据库库和附件中的端到端应用数据模型；不得新增依赖。
- 本项目自有：物理 Schema、Repository 事务边界、Job 租约/恢复、逐次尝试、Provider call 预留与审计。

交接报告必须记录实际复用、无需许可证归属的标准库来源、未引入第三方代码，以及为什么没有采用 ORM/外部 Schema。

## 唯一允许提交的 5 个文件

- `src/youtube_intel/state.py`
- `src/youtube_intel/migrations/001_initial.sql`
- `tests/integration/test_state_store.py`
- `tests/unit/test_state_transitions.py`
- `handoffs/TASK-003.md`

测试缓存、虚拟环境和 `dist/` 可由验证命令生成，但不得提交。不得修改 `src/youtube_intel/domain.py`、任何 Provider/编排代码、`pyproject.toml`、`uv.lock`、公共任务状态、ADR、其他测试或其他 worktree。若 `uv build` 证明 SQL 未打包且必须修改 `pyproject.toml`，停止并报告 `DECISION NEEDED`；不得与 TASK-004 竞争锁文件或工程配置。

## 已批准权限与红线

- ADR-003 S-01 至 S-08 的最终 Schema、migration、约束、事务、租约、逐次审计和任务卡验证已获产品负责人任务级批准。
- 只使用现有 Python 3.12、uv、标准库和已锁定开发工具；不新增或升级任何依赖。
- 默认完全离线，只使用临时文件 SQLite 与受控 UTC 时钟。
- 不连接真实数据库、不迁移或删除真实数据、不保存字幕/Provider 原始正文/密钥、不实现文件删除或退避算法。
- 不执行破坏性 migration、downgrade、清理命令、`reset`、rebase 或 main merge。

## 实现要求

### Schema 与 migration

1. `001_initial.sql` 必须逐列、逐约束、逐索引实现 ADR-003 S-01/S-02，不得简化 `scope_key`、`job_attempts`、Provider call 预留或全局 Job 唯一性。
2. migration 通过 `importlib.resources` 从包内读取；checksum 固定为 SQL 内容 SHA-256。
3. `schema_migrations` 是权威，`PRAGMA user_version` 必须镜像；名称/checksum/版本不一致时失败，不静默修复。
4. 每个 migration 使用 `BEGIN IMMEDIATE` 全有或全无；失败不得留下半建表、版本记录或错误 user_version。
5. 不提供 downgrade、删除或历史 migration 重写。

### 连接、类型与安全

1. 每个连接设置并验证 `foreign_keys=ON`、`busy_timeout=5000`、`synchronous=NORMAL`；文件数据库初始化并验证 WAL，不启用 `read_uncommitted`。
2. 时间只接受调用方注入的 UTC `datetime`，规范化为 ADR-003 指定 RFC 3339 文本；测试不得依赖本机时间或 SQLite 当前时间。
3. 对外使用具名参数和具名返回对象，不接收或返回自由形状 `dict`；可在 `state.py` 定义本任务需要的 Repository record 类型，但不得改变 `domain.py`。
4. 所有错误消息必须安全化；SQLite 不保存字幕、模型原始响应、密钥或绝对 Vault 路径。

### Repository 事务语义

至少实现 ADR-003 S-05 的八组语义：

1. 初始化与 Schema 版本查询。
2. 读取频道游标；以 expected cursor/revision 原子保存完整 `DiscoveryBatch`，候选和 `next_cursor` 全有或全无。
3. upsert 完整 `VideoMetadata`，允许更新标题等当前元数据，但不倒退 Pipeline、不覆盖 `discovered_at`。
4. 标记不可用候选，不用空字符串伪造完整元数据。
5. 以 `expected_status + pipeline_version` CAS 推进 Pipeline；调用现有领域转换语义，非法或陈旧转换零写入。
6. 创建、领取、续租、成功、失败、到期回收和人工重跑 Job，并保留 `job_attempts`。
7. 幂等 upsert Artifact；预留、读取、完成或失败 Provider call。
8. 按稳定周期键 upsert Report。

“候选 + 游标”“Job 成功 + 产物/调用索引 + Pipeline 推进”“migration”“周报记录”必须各自使用单一事务。使用故障注入测试证明任一步失败时全部回滚。

### Job 与 Provider call 恢复

1. 领取在 `BEGIN IMMEDIATE` 中稳定排序并 CAS，只允许一个 owner；领取同时递增 attempt 并插入活动 `job_attempts`。
2. 续租只允许当前 owner 且租约未过期；同步更新活动 attempt。
3. 过期回收记录 `LEASE_EXPIRED`，按剩余次数进入 `RETRY_PENDING` 或 `FAILED_FINAL`；到时后必须显式转回 `PENDING` 才能再次领取。
4. 成功/失败同时关闭活动 attempt；`attempt_count` 与最大 attempt number 一致。
5. 人工重跑创建新 `job_id`，不得改写旧 Job/attempts。
6. Provider call 使用 request hash 预留、owner/lease、available_at 和确定性 artifact 检查；只承诺 ADR-003 的 at-most-once best effort，不声称严格 exactly-once。

## 测试要求

先写失败测试，再做最小实现。至少覆盖：

- 初始化、重复初始化、checksum/name/user_version 不一致和 migration 失败回滚。
- 文件数据库 PRAGMA/WAL；临时文件多连接，不用内存数据库伪造并发。
- 候选与游标原子保存、空批次、expected cursor/revision CAS、批内故障回滚。
- 元数据 upsert、标题更新、`discovered_at` 保留、终态不倒退、语言 JSON 稳定化。
- 合法/非法/陈旧 Pipeline CAS。
- 视频与全局 scope 活动 Job 唯一性、稳定领取、双领取竞争、续租 owner/过期检查。
- `RETRY_PENDING -> PENDING`、租约到期、最大次数、人工重跑和逐次 attempt 审计。
- Artifact/Provider call 幂等与 reservation 接管；错误正文/密钥不落库。
- 阶段完成故障注入全回滚；周报稳定周期唯一性。
- `uv build` 的 sdist 与 wheel 都包含 `src/youtube_intel/migrations/001_initial.sql` 对应包资源。

不得删除、跳过或弱化 TASK-002 已有测试。不得为了减少实现量删表、删列、删约束或把关键场景改成只断言“无异常”。

## 执行流程

1. 复述目标、验收标准、Reuse decision、5 个允许文件和红线。
2. 核对：

   ```bash
   pwd
   git branch --show-current
   git rev-parse HEAD
   git status --short
   git config --get user.useConfigOnly
   git var GIT_AUTHOR_IDENT
   ```

   必须位于指定 worktree/branch/base，工作树干净，`user.useConfigOnly=true`，身份为 `Mozhu <huangbuqubunao@gmail.com>`；不符立即停止。

3. 使用测试驱动的最小增量实现；每个增量后运行最相关的聚焦测试。
4. 从 `handoffs/TEMPLATE.md` 创建 `handoffs/TASK-003.md`，加入 S-01 至 S-08 追踪表、Schema/checksum、事务/并发证据、构建归档证据、复用说明、跳过项与风险。
5. 运行全部检查：

   ```bash
   uv run python -m pytest tests/integration/test_state_store.py
   uv run python -m pytest tests/unit/test_state_transitions.py
   uv run python -m pytest
   uv run mypy src
   uv run ruff check .
   uv build
   git diff --check
   git status --short
   ```

6. 人工模拟一个 `RUNNING` Job 中断，推进受控时钟并回收；证明 Job 可再次调度且旧 attempt 仍可追踪。检查 sdist/wheel 文件列表并证明 migration SQL 已打包。
7. 完整复核 `dcc7d85d9d19f067dccdc2cdd12cdd2f5c438176...HEAD` 和所有未提交/未跟踪文件；范围必须精确落在 5 个允许文件，无数据库文件、缓存、构建产物、密钥或绝对私人路径。
8. 全部通过后创建范围明确的 commit，建议消息：`feat: implement SQLite state repository`。不得合并 main 或改变公共任务状态。

同一失败连续出现两次后停止重复方法，保留命令、关键错误、文件和尝试方案。任何 Schema/范围/依赖冲突必须返回主控，不得自行修改任务卡或 ADR。

## 最终输出

```text
Task: TASK-003
Role: Implementer
Branch/worktree:
Base commit:
Head commit:
Changed files:
Acceptance criteria: PASS/FAIL/BLOCKED per item
Checks: command + result summary
ADR-003 traceability: S-01 through S-08
Schema/migration evidence:
Concurrency/recovery evidence:
Build archive evidence:
Reuse evidence:
Diff review:
Skipped checks:
Remaining risks:
Decision needed: None | details
```
