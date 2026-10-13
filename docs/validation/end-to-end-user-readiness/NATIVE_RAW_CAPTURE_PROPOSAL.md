# 原生字幕回退：原始捕获文件的安全持久化提案

日期：2026-10-13。状态：**精确范围提案，尚未批准产品代码实现**。
本轮只允许写本文件；待旧 ledger 修复独立评审和整合后，再由主控指定新
独立 worktree、基线、实现者和 reviewer。本提案不表示资格、验收或正式采用通过。

续作授权记录（2026-10-13）：用户明确回复“批准该精确隔离捕获与恢复验收范围”。原精确提案保留；现在允许在其范围内实施，仍须等待旧 ledger 修复复审、整合及主控指定新独立工作树。没有更改旧 FAIL、正式数据或生产资格。

## 已确认的真实 P1

主控在 5928/5929 隔离验收服务执行 fresh normal import → 原生字幕回退 →
真实 macOS GUI Backup → ZIP 选择、Restore → 服务重启。独立快照显示：
71 张表逐行完全一致，完整 DATA 文件却从 **4 → 3**。缺失项为：

```
transcripts/0eMzc-WnBfQ/4944c4fbfa3665558c563da053e0d4571086df139588f504ce205c979694dc67/source.WyJhdXRvX3N1YnRpdGxlIiwiZW4iLCJlbiIsImpzb24zIl0.json3
SHA256 934957b468f8fc59a4bd5d57844e66702a65a78943c056a3472fed77b166caae
```

证据：本目录 `NATIVE_CAPTIONS_GUI_RESTORE_EVIDENCE.json` 保持 **FAIL**；
原始前后快照位于 root 的 `.var/end-to-end-user-readiness/captions-before-restore.json`
和 `captions-after-restore.json`。不得重标、覆盖、补写旧数据库来改变此次结果。
已经丢失的旧 JSON3 字节不能由 VTT、canonical 或字幕摘要反向还原。

根因已定位：`SubtitleAcquisitionService._fetch_reserved` 将被接受但无可靠
时间轴的第一份 JSON3 写入 DATA，然后原生 alternate 成功时重赋 candidate、
body、metadata、path。最终 `artifacts` 只包含选中 VTT 与 canonical，
第一份 JSON3 没有正规 Artifact 身份。Backup 正确只打包已索引文件，
Restore 正确按 manifest 恢复；生产者遗漏索引造成保存承诺失效。

已有测试仅证明 JSON3 仍在磁盘，未证明其 Artifact 身份和备份成员关系。
fresh 成功路径与 explicit caption repair 都受同一问题影响。

## 比此前批准范围新增的边界

此前 `CAPTION_REPAIR_PROPOSAL.md` 获批的敏感写入边界是：明确用户重试的
repair child **完成时**，原子持久化 winner raw/canonical、provider completion、
可信时间轴、Evidence 与 Job completion。它没有批准新的独立 pre-stage
持久化方法。

本提案新增的是：在已有 owned Job 与 subtitle provider reservation 下，
将真实获取并验证的 first plain 捕获 **在完成前** 固定其身份和 hash，写入
现有 `artifacts` 表；stage/repair 成功时再将其纳入完成事务的 artifacts。
这个捕获边界可能在 429、写盘失败、事务 rollback 或进程中断之后仍留下
非权威 raw 保存记录，因此须获具体批准并独立审查。它不授予 provider
success、Job success、当前 canonical pointer、时间轴、Evidence 或 Summary。

不将泛用 `upsert_artifact` 当作新安全校验边界；它目前仅检查基础字段及
重复 key 一致性，缺少本次所需的 owned lease/request/来源验证。

## 拟议的最小实现范围

### 捕获身份

- 原始捕获仍使用 `ArtifactKind.SUBTITLE_SOURCE`、`StorageRoot.DATA`、
  `LONG_LIVED`，model/expiry 均为 None；不是新 Schema、表或状态枚举。
- 捕获 identity 绑定当前 video、Job、provider 与版本、raw request hash、
  固定选择/格式政策和原始来源 metadata；content hash 为实际 raw bytes SHA256。
- key 使用单独命名空间，例如
  `subtitle-source-capture:{raw_request_hash}:{source_metadata_identity}`。
  `source_metadata_identity` 包含固定来源/语言/格式身份，**不包含 body hash**，
  防止把合法但已变更字节放到一个新 key 后绕过冲突检测。
- capture artifact id 具有明确的 capture-role 前缀，绑定 metadata、request、
  provider/version、body hash；与既有 winner raw id 不冲突。
- **不占用**选中来源的 `subtitle-source:{raw_request_hash}` key；provider
  `response_artifact_id` 始终指向真实 winner，cache lookup 仍只使用 winner。
- 若原生候选无可信时间轴而 plain 仍成为 winner，允许同一路径的 capture
  与 selected 两个身份引用相同 hash。既有 Backup 按路径归并多 Artifact
  且要求 hash 一致；不改 manifest 规则、不重复 ZIP entry、不删除 capture。
- raw 本身只被保存，不建立新的 canonical，不绑定 timed transcript/Evidence。
  任何 timed/Evidence/Summary 仍只来自原有被证明的 winner/canonical 路径。

### owned pre-stage 捕获与 CAS

新增一个窄 state 方法，供 `SubtitleAcquisitionService` 内部调用，无新外部
endpoint。事务内必须确认：

1. 当前 Job 属于此 video/pipeline/TRANSCRIPT stage；RUNNING，owner 相符且
   lease 未过期；repair 情况同时绑定当前用户 SourceRun 与确定的 repair child。
2. 当前 provider reservation 属于同一 owner，未过期，operation 精确为
   `subtitle.fetch`，model 为 None，request hash 与固定政策/版本/refresh identity
   可重算；状态不明或冲突按现有规则拒绝，不能偷用其他 reservation。
3. 来源 metadata、同源同语言原生回退选择、绝对 DATA root、deterministic
   relative path、大小、有效 UTF-8/plain 格式和实际 hash 均被验证。
   repair 的历史成功 Job/provider/raw/canonical/pointer 安全规则保持。
4. 同一 capture key 首次登记固定所有字段。重复完全相同记录幂等；hash、
   路径、Job、owner、来源、provider 或政策任一不一致拒绝，不 update/rebind。
5. 捕获登记不完成 provider/Job、不修改历史、不产生模型调用/费用。
   保护 gate、Backup quiescence 和已有预算/授权逻辑保持原样。

首次可信 body 获取和质量验证之后，**先固定 durable hash，再把该 body
原子写到确定 raw path**，之后才发起 alternate read。这样进程在写盘窗口
中断后仍有原 hash，可核验已有字节；不能仅以一个存在的 path 推断真实捕获。
活跃工作及 reservation 继续阻止 Backup，不能以 capture 记录放行。

写盘不是 SQLite 事务的一部分，以下窗口必须明确处理，而不能隐去：

- hash 已登记、文件未落盘：恢复只针对这一 capture record 的准确 path/hash。
  已失效 lease 按现有恢复规则重新准入；必要时同源有界重取，字节必须完全
  匹配固定 hash。不能把不同新字节作为旧捕获、覆盖记录或伪造成功。
- 文件存在且有 capture record：先校验 hash 再使用，合法格式但 hash 改变
  也拒绝；不额外 body read，不 rglob，不推广任意文件。
- 旧实现/中断留下的文件没有 capture record：仍是未知捕获，不能通过
  `expected_hash=None` 重归一化后自动登记；保留原文件、fail-closed。若安全
  重试需要新 request/generation，必须由现有用户命令与 Job 规则产生，不能
  偷改已成功历史或覆盖旧路径。若现有规则不能恢复，报告具体阻塞，另提
  精确受控恢复方案；不顺便扩大 runtime 行为。
- missing/corrupt 已登记 raw：Backup 继续拒绝；不能取消索引、绕过完整性或
  假装备份成功。明确恢复到原 hash 的字节或报告需要另批的具体处置。

### normal 与 repair 完成

normal completion 保持原 `complete_stage` 状态机，加入经过验证的 firstplain
capture ArtifactWrite；selected raw/canonical 和 provider pointer 不变。

`complete_caption_repair` 不再假定所有 artifacts 恰为两个位置项：明确解析
winner raw 与 canonical，另外最多接纳该次严格绑定的 capture。保留原有
Job/SourceRun ownership、旧成功来源、当前 pointer、native timing/exact text、
provider completion 校验。额外 capture 逐字节按 durable hash 重读，与已登记
capture 全字段 CAS 一致；拒绝任意额外 artifact/foreign source。

完成事务 rollback 仍不得留下 timed/Evidence/Job success/provider success。
先前真实 raw capture 记录和字节允许保留，代表捕获已发生；失败测试须区分
“raw capture 已保存”与“authority 未提交”，不得削弱原 authority 断言。

## 精确允许文件（获批后，独立新 worktree）

| 文件 | 限定变更 |
|---|---|
| `src/youtube_intel/transcripts.py` | firstplain capture 身份、受控登记调用、固定 hash 的精确恢复、完成 artifacts |
| `src/youtube_intel/state.py` | owned pre-stage capture 方法、CAS/lease/request 校验、repair 接纳精确额外 capture |
| `tests/integration/test_subtitle_provider.py` | fresh normal/429/损坏/恢复/事务失败 capture 证据 |
| `tests/integration/test_runtime_composition.py` | explicit repair、保护 gate/并发/lease/restart/旧历史不变 |
| 现有 Backup/Restore 集成测试文件 | 新 capture 完整表/文件往返验证，生产 Backup 代码不改 |
| 新任务卡和对应 handoff | 审批范围、实际检查和独立 review 证据 |

若现有 `TranscriptRepository` protocol 的声明需要新增窄方法，在
`transcripts.py` 内完成。`runtime_composition.py`、前端、transport security、
Backup/Restore 产品代码不在本提案允许写入范围；确需变化先向主控报告。

## 必须验证的安全与恢复结果

- Fresh normal JSON3→VTT 成功：capture/index/raw hash 存在，selected key 与
  provider response 仍是 VTT，canonical/time/Evidence/Summary 只绑定 winner。
- explicit repair 同样保存新增 raw；旧成功 Job/raw/canonical/ledger 逐字段不变。
- 无 alternate/invalid alternate 保持既有 plain 行为，多个同路径身份 hash 一致。
- 重复登记/重复 completion 幂等；两 worker 并发/过期 lease/外来 owner 均拒绝。
- foreign request/video/job/source/language/provider/version/path/hash 全部拒绝；
  包括修改成另一份**合法可解析**字幕字节，不仅 malformed 损坏。
- 429/未知 alternate 执行状态仍传播与阻塞，不降级成虚假成功；此前真实
  capture 有固定身份保存，重试不重复 firstplain body read。
- `stage.after_artifacts`、`caption_repair.after_artifacts`、
  `caption_repair.after_authority` rollback：只有允许的 capture 可持久存在，
  新 authority 全部回滚，历史不变；重新准入后正常完成。
- BaseException 进程中断、Job/provider live lease 和 lease expiry；hash-first
  文件尚未落盘窗口、file-present 窗口分别覆盖，不广扫未知路径。
- 未索引旧文件/缺失索引/损坏已有 capture fail-closed，不能冒充证据或绕过备份。
- Backup readiness 仍按真实全部任务/reservation判断；full table + **全部 DATA
  文件** path/hash/bytes exact 往返。测试 assert 不改成仅比较 indexed 子集。
- 恢复后 capture hash/Artifact/provider/Job/time/Evidence/Summary 完全一致，
  不复活任务、不执行模型、不增加 provider body call、无付费 Cloud。
- 完整 backend、frontend、TS/build、Ruff/strict mypy/diff-check；独立代码 review；
  fresh 新版本 5928/5929 或新隔离端口真实 macOS Backup/Restore 重新验收。

## 旧数据、风险与恢复策略

无 Schema migration，不改正式 owner DB/DATA 或 production config，不改依赖。
旧已索引 raw/provider/cache 语义保留；旧漏索引文件不自动 promotion。
已经成功的旧 repair 不因本修复被反复抓取或重跑。

未来如需补旧成功漏索引：先只读 inventory；必须有独立保存的原 path/hash、
来源/request/Job 捕获证据，逐条给出候选与不能证明的条目。另提具体补登记
范围并批准，不以当前文件的自算 hash 反证它此前是同一真实捕获。旧 Restore
已经丢失的文件明确报告不可恢复；fresh 新版本 PASS 不替代原 FAIL。

主要风险是 pre-stage raw 保存记录先于完成而存活，和 durable hash 与文件
落盘两阶段间的 missing-file 窗口；必须保留 fail-closed、受控精确恢复和
清晰失败证据。不能为了 readiness 引入删除、自动退役 capture 或 wildcard
manifest 打包。遇到无安全恢复路径时停止并报告，不能假称链路完整。

原生 rolling VTT 重复另属 normalization/timing/Evidence 政策问题：本提案
不改变 canonical、cue 时间、文本投影或 Summary 去重，不顺便增加功能。

## 执行门禁

1. 对本新增 pre-stage 持久化边界获得具体批准。
2. 等 ledger 实现评审/整合，主控指定新基线与独立 writer worktree。
3. 批准范围内 TDD、完整回归、独立 reviewer、隔离真实 GUI/Restore 验收。
4. 正式采用仍须主控与用户依据整个 goal 的安全条件另行决定。

当前不创建新 writer worktree，不实施产品代码，不触碰旧 FAIL 或正式产品。
