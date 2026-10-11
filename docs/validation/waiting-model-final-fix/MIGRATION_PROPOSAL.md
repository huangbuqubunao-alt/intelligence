# WAITING_MODEL 安全终止：精确迁移审批包

状态：Owner 已在 2026-10-11 明确批准本精确范围（“批准该精确迁移范围，继续实施和验收”）。
迁移已在候选分支及隔离数据库实施；正式采用仍须全部验收通过。
基线：`9f3b03ead107b769b81bf1c77f76d542a424921c`，现行 schema 36。

## 原因与方案

m010 的 `distillation_checkpoint_terminal_immutable` 禁止修改 WAITING_MODEL；
resource usage 同样不可变。既有 source-run 取消不能终止其独立 checkpoint。
不把等待当成功、不删除或更新原 checkpoint，不复用 no-new 成功记录。

追加 migration 037：新增 `distillation_waiting_model_cancellations` 一张表。
字段：execution_id（主键、checkpoint 外键、ON DELETE RESTRICT），source_id、
video_id、reason、use_case、selected_provider、selected_model、output_language、
原 checkpoint updated_at、budget_state、cancelled_at，固定 outcome
`CANCELLED_BEFORE_MODEL_INVOCATION`。这些字段绑定不可变请求及确切等待状态。

仅新增该表的 INSERT 安全校验、UPDATE/DELETE 不可变 trigger，以及针对已取消
execution 的 checkpoint/相关执行产物写入保护 trigger。不重建已有表、不删除
数据、不修改已接受的模型资格、云授权、预算、Evidence/no-new trigger。
不扩展 PENDING、RUNNING、WAITING_BUDGET 的取消权限。

## 安全校验与生命周期

取消在 `BEGIN IMMEDIATE` 内读取、校验并插入，重复请求返回同一终止结果。
前提是原 checkpoint selected_provider=ollama / WAITING_MODEL / invocation_count=0 / 无 Intelligence 或
revision；同一 execution 的不可变 usage 必须完整匹配请求和预算身份，且为
WAITING_MODEL / invocation_count=0 / MODEL_UNAVAILABLE_BEFORE_TRANSPORT。
实际 provider/model、token、费用、duration、HTTP response 必须均为空。
已 claim/未知 budget marker、no-new 或云响应/失败记录拒绝。
云端任务不获得本地取消权威，保持既有授权、前置失败记账与 fail-closed 规则。
source-run 如仍活跃，或关联身份/child 状态矛盾，拒绝并允许稍后重试。

原 checkpoint 和 usage 保持原字节语义；有效结果由经重新验证的 sidecar
投影为 CANCELLED。继续执行、重启恢复均先读此权威结果，不重新调模型。
取消与启动共享 SQLite 写事务和既有 claim CAS：已调用/未知执行不能成功取消。
新记录不能使另一个 execution、关联 run 的其他 child 或其他任务变为终态。
关联 settled NEEDS_ATTENTION run 保留历史，不伪造 COMPLETED；Backup 仅在每个
child 均有匹配合法终止权威时承认静止，并继续检查所有其他任务。

## 旧数据兼容与恢复

迁移时新表为空，不自动取消历史等待任务；旧记录必须经相同严格校验后由用户取消。
schema 36 备份恢复到新版时按现有 migration 流程升级，原等待仍阻塞；schema 37
备份携带 sidecar，经完整性与语义验证后恢复，已取消任务不复活。
缺失 ledger、损坏/不一致 sidecar、未知执行状态 fail-closed。

只在隔离测试 DB 演练迁移和恢复；正式 owner 数据不用于测试或重置。
正式采用后只运行经批准的追加迁移。部署前保留正式数据库及 DATA 的安全快照；
失败时停止采用，不 reset 数据、不强退 schema、不自动删除新表。
代码回退须与 schema 兼容；旧代码不识别新取消结果会保守阻塞备份，不会重派
WAITING_MODEL。必要的数据恢复只采用已验证备份与现有 restart-boundary restore。

## 风险与验收

风险：新的终止权威若验证不足可能错误放开备份；需要同时测试 SQL 直接写入、
损坏记录、并发 claim、重启、旧备份、新备份、其他 active child 和云执行。
加表/trigger 会改变 schema 指纹，必须核实 Backup schema allowlist/校验与完整回归。
不引入依赖、不扩大功能、不启用未合格模型、不产生付费请求。

授权来源：本次用户 Goal 要求正规持久化终止，但同时要求敏感迁移具体批准；
仓库 `AGENTS.md` §5 明确禁止未经具体批准修改 Schema。
