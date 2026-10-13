# TASK-READINESS-NATIVE-RAW-CAPTURE 交接报告

## 元数据

- Task: TASK-READINESS-NATIVE-RAW-CAPTURE
- Role: Implementer /root/source_context; Reviewer: /root/intel_bounded_review
- Base: c5da5e8007f8a1343207045d5203558e0a8f253d
- Worktree: /Users/hua/Documents/yia-worktrees/readiness-native-raw-capture
- Branch: codex/task-readiness-native-raw-capture
- Head: implementation commit identified by this branch and root report; no main merge.
- Reported: 2026-10-13
- Suggested status: IN_REVIEW; root owns final acceptance.

## 目标与精确批准

原生 JSON3→VTT 的真实 GUI Restore 留下原 FAIL：完整 DATA4→3。只修生产者遗漏 raw index，不改 Backup 判定、旧证据或正式数据。

用户已具体批准 root 的 NATIVE_RAW_CAPTURE_PROPOSAL.md 及 NATIVE_RAW_CAPTURE_ADDENDUM.md（“批准该精确补充范围，继续实施和验收”）。补充将同一个 owned hash-before-file 边界扩至实际接受的 timed primary 或单次同源 native winner，每 request 最多两个 capture。root 维护提案，本实现不重复提交提案副本。

## 实际实现 / 复用

DIRECT：标准库 SHA256/SQLite BEGIN IMMEDIATE/atomic fsync write、现有 ArtifactWrite full-field CAS、owned Job/provider leases、固定 subtitle selection/format request identity、原始文件 UTF-8/质量验证、immutable SourceRun/repair child identity、旧 plain source request/raw/canonical 验证、现有 Backup/Restore。无新依赖或许可变化。

- transcripts.py：独立 capture-role key/id；key 不含 body hash。实际接受且验证过的 body 先调用窄登记方法，提交 durable hash，再按该 hash 原子写 DATA。已有 capture 仅精确 hash 校验后复用；hash-only 窗口只能同源有限重取并全字段 CAS；未知旧 raw path 不读正文、不推广、不覆盖。
- state.py：register_subtitle_source_capture 在同事务确认 bound DATA、Job/video/pipeline/stage/scope/当前 lease、provider request/policies/版本/refresh/当前 reservation 和未知 dispatch 状态；repair 同时复核当前显式 SourceRun/child、历史成功源的文件与完整 request/raw/canonical 身份。同 key 完全一致才幂等，任何不同合法字节也拒绝。第二 capture 只能是同源同语言、首份无 timing 后的已接受 VTT/SRT；最多两个。
- capture 仅 LONG_LIVED SUBTITLE_SOURCE 原料；不完成 provider/Job，不授 canonical/timed/Evidence/Summary。
- complete_caption_repair 明确解析 selected source/canonical，接纳 1–2 个全字段 CAS 精确预登记捕获；登记 membership、hash、path、provider/version/metadata 和实际 winner 全部绑定。事务回滚仍回滚全部 authority，仅独立已捕获 raw 记录留存。
- winner key/provider response 指针与 canonical identity 不变。相同 raw path 的 capture/selected 两身份由既有 Backup 按相同 hash 归并；无 manifest 修改。
- 构造器复用 bind_source_storage(data_root) 既有不可重绑定规则（root 明确认可）。根是可信显式参数，不推断。未绑定直接登记/外来根拒绝；同根幂等、构造冲突无数据库变化。

REJECT：unknown expected_hash=None promotion、重取未知旧文件补登记、正文 hash 进入 key 绕冲突、历史改写/删除、伪造时间或 Summary、Cloud/模型 fallback、wildcard Backup、仅比较 indexed 子集。

## TDD / 验收证据

| 项目 | 结果 / 外部证据 |
|---|---|
| 初始 RED | /tmp/readiness-native-raw-capture-red.log：first plain JSON3 存在但 captures=0，assert len(captures)==1 失败。保留复现，获批 max2 后断言精确两捕获。 |
| 正常/repair | winner 仍是实际 VTT；plain 与 winner raw indexed，canonical/timing/Evidence 不引用 capture-role；旧 successful Job/raw/canonical/history 不变。 |
| 两阶段窗口 | before_commit 无捕获；hash-only 有 hash 无文件可只按同字节重取；file-present 精确 hash 复用、零第二 body GET；primary + alternate 都覆盖。 |
| CAS / 并发 / 异常 | 同 root/重复登记/并发同捕获幂等；foreign owner/job/video/provider/version/language/request/generation/path/hash/body/kind/root/unknown dispatch/expired lease 拒绝；第三 format 拒绝。 |
| 合法不同字节 | existing capture 文件被合法字幕字节替换拒绝且不再 GET；hash-only refetch 的不同合法 body 拒绝，原 hash/记录不变。 |
| 429 | 首 plain durable 捕获保留，无 authority；重试只读 VTT，formats=[json3,vtt,vtt]。 |
| rollback/restart | 原 zero body reread 成功断言保留；精确捕获数 + 非 capture 产物零 + timed/Evidence/Summary/provider success rollback，不再混淆捕获与 authority。 |
| 完整 Backup/Restore | test_native_capture_backup_restore_preserves_every_table_and_every_data_file：所有 SQLite table 逐行相等，全部 DATA path/bytes/hash 相等，含初始 plain 与 repair plain/native 三 capture。无 provider 增量，Summary/timed/Evidence可验证。 |
| missing/corrupt Backup | 原 capture hash 保留，缺失或合法修改的 raw 不能创建成功备份；没有删除索引放行。 |
| ASR tuple | 实際 current_tuple 与 accepted root 逐字段完全相同；SHA256 9df8c083899990ebb7ad1e9173ccb6f4cb663351b78c4f0286b371443b04c357。仅本地 manifest/文件哈希/工具版本重算，无模型执行，不新 mint receipt。 |

## 检查结果

- 扩展 13 文件：419 passed in 142.68s，/tmp/readiness-native-capture-expanded.log；包含 subtitle/provider、runtime composition、Research/DA BackupRestore、Backup 单测、LocalContent/adversarial、offline/local transcription、acoustic qualification/remediation。
- 加强登记历史 proof/ledger 之后完整两修改测试文件：188 passed in 59.53s，/tmp/readiness-native-capture-final-targeted.log。
- 最后 provider metadata/cache 行与聚焦复核：48 passed, 140 deselected in 34.00s；/tmp/readiness-native-capture-final-review.log。
- Ruff check 两生产+两测试文件 PASS；strict mypy 两生产文件 PASS；py_compile 两生产+两测试 PASS；git diff --check PASS。
- expanded 唯一 warning 为已有 duplicate ZIP entry 的攻击 fixture，非新增警告。
- root 负责整合后完整 backend/frontend/TS/build 与 fresh macOS GUI 真实全部文件 Backup/Restore；实现者没有把这些标为已完成。

## Diff 复核

仅 state.py、transcripts.py、两对应 integration tests、本任务卡和本 handoff。没有 Schema、Backup/runtime/API/frontend 产品代码、依赖/锁文件/config/credentials、normalization/timing policy、ASR-bound tuple 实现、正式 DB/Vault/付费云、资格激活或 main/push。旧 FAIL 不变。新增测试计数明确区分获批 raw 捕获与不应提交的 authority，没有删除/跳过/减弱 zero-reread 或 ALL DATA 断言。

## 失败、风险与待 root 工作

已解决：原未索引 raw、原 unindexed recovery hash-less promotion；首次扩展回归中的 artifact 总数变化按精确 capture/authority 分类收紧，CLI 显式 DATA binding 复用已获 root 同意；新 unknown-dispatch negative fixture 使用真实 isolated dispatch row（原 subtitle 无 dispatch row，不能直接 record_intent）。

保留 fail-closed：旧无 capture 的 raw 文件不可自动恢复；旧 Restore 已丢失 bytes 不伪造；合法改变/损坏/缺失 raw 要由精确 hash 的安全恢复证明，不能绕过 Backup。

**整体 readiness 的原有窗口仍 OPEN，超出本次 raw 批准范围**：ordinary caption-repair completion rollback 后用明确新 child 重试，timed/Summary 可成功，但旧 current-policy FAILED_RETRYABLE provider ledger 仍 unresolved；旧 child 的非权威 derived canonical 文件未索引且保留。一次真实 isolated runtime audit 得到 readiness=false，唯一 reason=PROVIDER_CALL_UNRESOLVED、1 unresolved current-policy call、1 unindexed derived canonical，所有 raw 均已 indexed。没有删除/推广 canonical 或擅自退役 current policy ledger；同 child 的成功恢复会正规登记原 canonical。root 已收到风险，整个 goal 不能仅凭本 fresh成功 roundtrip 宣称全链路完成。

独立 review、root 整合/最终完整回归与 fresh GUI 未执行；正式采用未授权。本任务建议 IN_REVIEW，等待 reviewer verdict。

## Reviewer / 主控

Reviewer 结论：待独立审查，不由 Implementer 填写。
主控验收 / 整合 / DONE：待 root 决定。
