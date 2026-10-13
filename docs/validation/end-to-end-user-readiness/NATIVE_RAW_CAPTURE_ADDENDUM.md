# 原始字幕捕获补充范围：真实 winner 在完成前固定 hash

2026-10-13。状态：已获具体批准；原提案已获批范围继续有效。

用户明确回复：“批准该精确补充范围，继续实施和验收”。允许按以下范围实施，
仍须独立审查、完整回归与真实隔离恢复验证；不授权正式采用。

## 已确认的边界缺口

原获批 `NATIVE_RAW_CAPTURE_PROPOSAL.md` 仅包含 first plain 捕获，且 repair
完成“另外最多接纳该次严格绑定的 capture”。只保存 JSON3 无法证明完成事务
回滚后留下的 VTT 字节。此前测试明确要求相同 child 恢复成功而不再读取 body：

- `test_unindexed_native_raw_recovery_keeps_timing_without_second_body_read`：
  `opener.formats == ["json3", "vtt"]`。
- `test_caption_repair_restart_retains_command_child_and_raw_after_lease_expiry`：
  `adapter.read_calls == reads`。
- timed-primary rollback：`opener.calls == body_calls_before`。

未知旧文件不能以当前自算 hash 补登，也不能删除或放宽这些成功断言。

## 精确新增范围

把原 first-plain 的同一个 owned pre-stage 捕获边界，扩展到该次请求实际接受、
质量验证通过的原生 winner：包括 timed primary，或同源同语言的单次 VTT/SRT
alternate。先持久化实际获取字节的 hash/完整 capture 身份，再原子落盘。

每次请求最多两个 capture：首份 plain 与一个接受的原生 alternate；timed
primary 或无回退最多一个。重复 capture 完全相同才幂等，合法但不同字节也拒绝。
不捕获被拒绝的格式，不扩大网络读取次数，不重取未知旧路径来补登记。

repair 完成最多接纳两个经预登记、全字段 CAS、精确 path/hash 验证的 capture。
winner/canonical/provider response 身份和成功提交规则不变。只有原始捕获记录
允许在完成 rollback 后保留；timed/Evidence/Summary/Job/provider success 仍回滚。

所有原提案的 owner、lease、Job、SourceRun、request、provider、版本、来源、
语言、路径、UTF-8、hash 校验及 Backup gate 保持。追加 timed-primary 和 alternate
在登记前/登记后/落盘后/完成回滚、重启、过期 lease、重复调用、不同合法字节
拒绝及完整全部 DATA Backup/Restore 验证。原 FAIL 记录保留。

## 不变范围与风险

只使用原提案的文件及现有 Artifact 表；不改 Schema、Backup 规则、正式数据、
凭据、生产配置、依赖、模型资格或 normalization/timing 政策。capture 不授予
Evidence 或成功状态。缺失/损坏固定 hash 的文件仍 fail-closed。

新增风险仅为 winner capture 同样在完成前可持久存在，必须通过同样的所有权
与两阶段 missing-file 恢复检查。无破坏性迁移。批准后独立实施、审查、整合和
fresh 真实 GUI 全部文件恢复验收；本补充不授权正式采用。
