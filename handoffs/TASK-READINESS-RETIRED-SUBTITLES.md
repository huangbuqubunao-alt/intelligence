# READINESS-RETIRED-SUBTITLES 交接报告

## 元数据

- Task: `READINESS-RETIRED-SUBTITLES`
- Role: Implementer `/root/source_context`; Reviewer: `intel_bounded_review`（待独立审查）
- Base: `fbe0e2b7323384ebb60408a436c4a6b732c61a72`
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-retired-subtitles`
- Branch: `codex/task-readiness-retired-subtitles`
- 日期: 2026-10-13
- 本报告与实现同一提交；提交 SHA 由提交后主控回传记录，不自指哈希。

## 目标、授权与范围

用户明确批准原 root `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/docs/validation/end-to-end-user-readiness/RETIRED_SUBTITLE_FAILURE_PROPOSAL.md` 的精确隔离整改与验收范围。本提交不代表正式采用。

仅新增 `SQLiteStateRepository.retire_known_failed_subtitle_calls` 及正常后台 idle 维护挂接、专用测试与任务/交接文档。对已退休的 `subtitle.fetch/yt-dlp/model=NULL/subtitle-selection-v1/subtitle-format-v1` 已知 RATE_LIMITED 失败，在全局真实 quiescent 时从 FAILED_RETRYABLE 持久化为 FAILED_FINAL。原 error code、原错误文字前缀、request_hash/版本/计数/开始时间等均保留，追加固定 POLICY_RETIRED 原因和结束时间。

DIRECT 复用项目现有 provider ledger、SQLite BEGIN IMMEDIATE/CAS、BackupRestore 同数据库 protected gate/staged lock、既有核心数据库验证和 quiescence 判定、合法 WAITING_MODEL 取消权威。标准库 threading/SQLite 与现有 pytest；未加入或适配第三方组件，既有批准组件/许可证按 REUSE_REGISTER/NOTICE。REJECT 批量清空失败、未知 dispatch 当已知失败、绕过 Backup、改成成功、删除历史。

## 安全实现

- 匹配真实同数据库的 BackupRestoreService；恢复/重启窗口、其它保护窗口不执行。
- 同一 BEGIN IMMEDIATE 内检查所有非终态 provider：只有精确旧政策、明确已知错误、无 owner/lease/response/token/费用、无未知 dispatch、无已索引原始响应才可终止；存在任何其它 provider 整批不动。
- 原样复用 Backup 全局验证：Job、Source Run、source_checks、未终止 checkpoint、其它 dispatch 仍 fail-closed。合法取消 checkpoint 通过现有记录读取，未改 raw 状态或 Backup 安全判定。
- CAS 只终止仍保持同一 retryable 记录的请求；旧请求重新领取与终止互斥。当前政策新请求独立保持正常生命周期。
- 启动恢复及普通工作完成后的 idle worker 自动尝试维护，用户无需直接 SQL。维护关闭自身窗口的同步 wakeup 以 thread-local 抑制，外部线程通知和普通用户 notify 保留，防止后台自唤醒循环。
- BackupRestore 源码、Schema、正式配置/数据、凭据、模型资格、云授权/预算均未修改；无网络/GPU/模型调用。

## 验收证据

| 验收项 | 状态 | 证据 |
|---|---|---|
| 旧429 + 当前政策成功仍受旧 ledger 阻塞，正规终止后 readiness 开放 | PASS | 专用测试保留当前政策成功记录及旧失败 error/hash |
| 幂等、重启不复活、Backup/Restore 数据一致 | PASS | 真实 archive create/stage/confirm/recover，全表快照一致；旧 request 再次 reserve 不获得执行权 |
| 历史完整 | PASS | 所有业务表快照除该 provider 状态/追加文字/完成时间之外一致，原 checkpoint/dispatch 记录保留 |
| 不确定/真实任务 fail-closed | PASS | 云/模型/当前或未知版本、原始响应、token/费用、租约/过期 owner、五种不一致 dispatch、其它 provider、Job/sourceRun/sourceCheck/checkpoint/Restore 负控 |
| 并发互斥 | PASS | 两线程旧 request reserve vs retirement 单一赢家；事务内检查时新 request 只能等事务结束，新 PENDING 仍阻塞 Backup |
| 正常后台维护 | PASS | 实际 DurableSourceRunWorker idle 挂接、无自唤醒、外部同步/跨线程通知不丢失 |
| 独立审查、真实 GUI、完整产品验收 | 待主控 | 此提交仅 scoped 实现与自动测试，不宣称整个普通用户链路可用 |

## 检查结果

- TDD 首次 RED：`PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/test_retired_subtitle_failures.py -k retired_known_failure`；缺少终止方法 AttributeError。
- 后续首次扩展测试中的 3 个失败为新 fixture 使用错误 API（canonical TRANSCRIPT scope、claim_next_job、complete_provider_call kwargs）；逐一对照实际契约修正，未修改既有测试或生产契约。source-check fixture 后续遇到 SOURCE_UNTRUSTED，因为旧 helper UC_TEST 不是可验证频道；改为独立真实形状的 canonical channel 跟踪 fixture，没有放宽验证。
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/test_retired_subtitle_failures.py tests/unit/test_backup_restore.py tests/integration/test_runtime_composition.py tests/integration/test_background_following.py tests/integration/test_state_store.py tests/integration/test_task022_personalized_distillation.py tests/integration/test_task023b_distillation_reservation.py`：**358 passed in 173.47s**，含专用 39 案例。一个既有故意构造 duplicate ZIP path 负向测试触发标准库 UserWarning，没有失败。
- Ruff、strict mypy 两个生产文件、py_compile 三个变更 Python 文件、git diff --check：PASS。

## Diff 复核、跳过与风险

允许范围内仅 state.py/runtime_composition.py/专用测试/任务/交接文档；无无关重构或格式化 churn，未改已有测试、BackupRestore、迁移、依赖、配置、正式数据。测试仅独立 tmp_path 数据库/文件。

本 scope 未跑前端/build/GUI 或完整后端，因没有前端变化且由主控整合后统一验收。已复用现有 Backup 私有 protected gate/验证接口，因此其未来修改需同步维护本调用；本次独立 Reviewer 应重点检查锁顺序、并发和 fail-closed。损坏数据库会沿用验证异常拒绝维护，worker 既有异常循环延迟重试，不修复/忽略损坏。没有使未合格本地模型获生产资格。

## 实现者结论

建议 `IN_REVIEW`，禁止自行合 main。`DECISION NEEDED`: None（已获精确隔离批准）。

## Reviewer / 主控 / 整合

待独立 Reviewer 和主控记录；本实现者提交后停止写入，不预填 APPROVE/ACCEPT/DONE。

### 独立 Reviewer — REJECT（2026-10-13）

- Reviewer `/root/intel_bounded_review`；审查范围 `fbe0e2b7323384ebb60408a436c4a6b732c61a72...2c71a9750fb155d02fb41e1227a83809301b66e6`，没有修改业务代码。结论 **REJECT：P0=0，P1=1**。不能整合或声称已完成安全验收。
- **P1：无法正规读取的 ledger 历史仍被自动终止并放行 Backup。** `state.py:4332–4343` 只读取原始 dispatch status、比较时间字符串；没有通过现有 `ProviderCallRecord` / `ProviderDispatchRecord` 解析权威记录。`_verify_core_database` 不解析这些字段，因此不是补偿校验。
- 独立复现使用专用测试的 `_workspace` / `_failure`，每例均为新的 `TemporaryDirectory(prefix="retired-subtitles-independent-")`。正常已知429失败记录之后，分别仅将 `provider_calls.started_at`、`updated_at`、`available_at` 或既有 `FAILED_KNOWN` dispatch 的 `updated_at` 改为字符串 `0`。正规 `get_provider_call` 或 `_dispatch_state_in_transaction` 均报 `ValueError: Invalid isoformat string: '0+00:00'`。四例均被 `retire_known_failed_subtitle_calls` 转为终态，Backup readiness 从 `False / PROVIDER_CALL_UNRESOLVED` 变成 `True`，而损坏历史没有获得可解释权威。这些修改仅发生在隔离临时测试数据库，未触碰正式数据。
- 必须在同一个 `BEGIN IMMEDIATE` 内对所有拟退休 provider 与存在的 dispatch 使用原正规解析器并校验适用时间关系；不可解析、无法解释或不一致的记录必须整批拒绝且不改任何行，继续 fail-closed。补充四种损坏时间与有效/损坏记录混合批次的原子不变负控。不要修改 Schema、Backup 安全判断或旧历史字段来掩盖失败。
- 已核对正常保护窗口锁顺序与 Backup 相同；SQLite事务/CAS互斥现有 reservation；非目标 provider、未知 dispatch、活动工作和合法取消 checkpoint 的正常规则保留。thread-local 只抑制本维护关闭窗口的同线程自唤醒，普通 `notify()` 与跨线程通知仍保留。没有发现另一项独立 P1。
- 独立运行实现者列出的七个完整相关测试文件：**358 passed，1个既有 duplicate ZIP path UserWarning，175.66s**。命令为 `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/test_retired_subtitle_failures.py tests/unit/test_backup_restore.py tests/integration/test_runtime_composition.py tests/integration/test_background_following.py tests/integration/test_state_store.py tests/integration/test_task022_personalized_distillation.py tests/integration/test_task023b_distillation_reservation.py`。日志 `/tmp/readiness-retired-subtitles-review-tests.log`。现有测试通过没有覆盖上述独立 P1。
- 独立 Ruff（三个 Python 文件）、strict mypy（两个生产文件）、`git diff --check` PASS。与 root `d903c60` 的只读 `git merge-tree --write-tree d903c60 2c71a9750fb155d02fb41e1227a83809301b66e6` 无冲突，结果树 `272fca3f489e277bf95a64bfc84a0ab7868bc3aa`；未实际合并。frontend、完整后端和真实GUI不在本次纯后端 scoped reviewer 检查内，不能据此声称全链路通过。未运行网络、模型或正式数据操作。

### Implementer — P1 退回整改（2026-10-13）

- 正式退回基线 `22be1a4a1e052673edcc140dadd697bd1656fa5b`，保留原实现与上述独立 REJECT 历史；本节是新的 scoped 修复证据，不改写审查结论。
- 原缺陷确认：把 raw TEXT 时间大小比较及数据库 schema 校验当成了可解释 ledger 历史证明，遗漏正规 ProviderCallRecord / ProviderDispatchRecord 读取。
- 同一 BEGIN IMMEDIATE 内，对每个候选复用 `_provider_call_from_row` 及 `_dispatch_state_in_transaction`。明确 ValueError/TypeError/OverflowError 解析失败则整批返回不变，未使用宽泛异常来绕过校验；不存在新状态或修复历史数据。
- 完整行读取后检查请求哈希的64位小写hex形状、真实整数且正的 reservation attempt_count、原三个时间字段均为字符串/可解析 UTC，started_at <= updated_at <= 当前时间，available_at >= updated_at。未来的有效 retry backoff 仍允许安全终止并原样保留，不把 backoff 视为未知 dispatch。
- 存在 dispatch 时必须是正规解析的 FAILED_KNOWN、request_hash 同一关联，且其 UTC 更新时间在开始与已知失败更新时间之间。date-only 被原 parser 接受为 naive datetime，不具备 UTC 执行时间权威；本方法明确拒绝，不改全局 parser。
- 所有行校验先于任何终止 UPDATE，因此一个损坏行与多个合法行混合时也不部分清理。原 owner/lease/response、未知 dispatch、全局工作/Restore 及 CAS 判定完整保留；BackupRestore/Schema/runtime hook/Cloud/正式配置和数据没有新增改动。
- request_hash 的原 normalized input 不在 provider ledger 持久化字段中，本补丁验证既有身份形状和 dispatch 关联，不伪造或重算缺失原输入，不宣称对已合法形状的历史哈希进行语义重新归属。

新增 TDD 证据：

1. 改实现前 `PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/test_retired_subtitle_failures.py -k 'unreadable_retirement_history or inconsistent_retirement_times'`：**16 failed / 39 deselected**；四种时间 `0` × 单行/混合批次全部错误终止，时间关系/计数异常同样错误终止。完整日志 `/tmp/readiness-retired-subtitles-p1-red.log`。
2. 初轮加入正规 parser 后 54 passed / 1 failed：原 FAILED_KNOWN 正控 fixture 使用 `NOW.isoformat()`，正规 parser 不接受 `+00:00` 文本。对照实际生产 `format_utc_datetime` 的 Z 写入格式修正 fixture，保留全部正控断言；时间关系负控也改成正规可读 Z 格式，以确保检查的是合理关系，而不是仅因解析错误通过。
3. 新增20个负控：四个损坏时间、四种混合批次、可正规读取但不合理的时间关系、非真实整数/零/未知计数、四个无 UTC 的日期；另加一个未来合法 backoff 正控。全部进行业务表快照不变与 Backup 仍阻塞检查。
4. 专用测试最终 **60 passed in 17.01s**；py_compile / Ruff 三 Python 文件 / strict mypy 两生产文件 / diff check PASS。
5. 原七文件完整相关回归：**379 passed / 176.32s**，仅一个既有 duplicate ZIP path UserWarning（预期破损备份负控）。完整日志 `/tmp/readiness-retired-subtitles-p1-regression.log`；未跳过/削弱测试或更改测试脚本。

本次实际新增生产修改仅 state.py 退休方法；专用测试 fixture/负控及本交接文档。后端全产品和真实 GUI 仍由主控整合后验收。建议重新 `IN_REVIEW`，不自填独立 APPROVE，也不自行整合/main采用；提交后停止写入。

### 独立 Reviewer — P1 修复复审 APPROVE（2026-10-13）

- `/root/intel_bounded_review` 审查 `22be1a4a1e052673edcc140dadd697bd1656fa5b...b9bb62c8cc30de4e2900424d7c36ed2cf46333ee` 并复核原 scoped 实现。**APPROVE，P0=0 / P1=0**；原 REJECT、失败记录及实现全部保留。本结论只批准用户已授权的隔离退休维护实现，不是正式数据变更、main采用、模型资格或整体GUI验收。
- 独立重放四种原始损坏时间字段，每种单行/与另一个正规已知失败行混合共8例：均返回空退休集合，所有业务表快照完全不变，Backup 继续 blocked。独立未来合法 backoff 正控安全终止且 available_at 原样保留，readiness正确开放；不是仅复用作者断言。
- 确认正规 provider/dispatch 解析与 hash/count/UTC/时间关系检查均在同一个 BEGIN IMMEDIATE 内且先于任何 UPDATE，混合批次不会先写合法行。解析失败不修复/覆盖旧时间；原未知/Cloud/owner/lease/response/费用负控、全局quiescence、保护窗口与CAS仍保留。没有改 Backup安全判断、Schema或全局时间解析器。
- 独立重跑原七文件完整相关测试：**379 passed，1个既有 duplicate ZIP path UserWarning，183.33s，无跳过**；日志 `/tmp/readiness-retired-subtitles-rereview-tests.log`。完整命令同上次审查，包含专用60例、BackupRestore、runtime/background、state、云/本地 distillation reservation。原 race、重启、真实archive恢复、全表历史与外部通知负控全部通过。
- 独立 Ruff（三个 Python 文件）、strict mypy（两个生产文件）、py_compile、diff check PASS，业务 worktree在审查前后 clean（本追加审查记录除外）。与 root `08e02e2` 的只读 merge-tree 无冲突，结果树 `c013250383a321834c452eb797f7b20ec09c8eb5`，未实际合并。
- 只写本handoff审查段，未改业务代码。完整产品后端回归及真实GUI维护→BackupRestore仍由主控整合后完成，未运行模型、网络或正式 owner 数据。
