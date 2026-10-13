# 字幕失败后成功重试：安全终止与非权威文件归档迁移提案

2026-10-13。待具体批准，未实施。仅隔离整改与验收，不授权正式迁移/采用。

## 实际P1与不能采用的捷径

独立正常API/worker+精确completion事务回滚复现：显式新child补全成功，旧current-v2字幕请求仍FAILED_RETRYABLE，Backup为PROVIDER_CALL_UNRESOLVED；原失败事务留下一个未索引derived canonical。raw捕获补丁只解决真实raw的持久化，未引入该缺口。旧v1/429退休审批不覆盖当前政策。

现Backup create只打包Artifact索引；仅把旧ledger终止会让派生文件静默遗漏。不得删除文件，不得伪登记成原始字幕，不得补成canonical权威、不倒填时间或授Evidence。必须同时保留真实文件并证明终止安全。

## 精确Schema37→38范围

只新增文件migration038及一张不可变表 retained_subtitle_derivations，不重建旧表、不修改原CHECK、不回写历史。字段固定为：archive_id（主键）、proof_version、request_hash、job_id、source_run_id、source_id、video_id、raw_capture_artifact_id、raw_sha256、relative_path、derived_sha256、size_bytes、normalization_version、quality_profile_version、canonical_request_hash、successor_job_id、successor_request_hash、successor_canonical_artifact_id、successor_summary_artifact_id、reason、created_at、proof_json、proof_sha256（共23字段）。均非NULL；hash/size/relative-path/枚举/时间在服务边界严格验证并给数据库能表达的CHECK；request/Job/SourceRun/source/raw/后继Artifact采用现表FK。追加UPDATE/DELETE拒绝triggers，索引仅按request/job/path查重。同path不同bytes/identity必须拒绝，重复相同proof幂等。归档表任何reader不得视作Transcript/Evidence/成功输出来源。

原有FAILED_FINAL已受schema支持。旧请求終止与归档索引在同一BEGIN IMMEDIATE、protected operation gate及restore/stage锁下CAS完成；保留requesthash、policy、attempt计数、原错误、原Job/attempt/SourceRun全部历史，仅CAS更改ledger status/finished_at/updated_at，原error/message/attempt/available_at不改；明确终止原因只写不可变归档表，不伪成功。已有字幕GET历史必须如实保留，不声称零历史调用；操作本身不额外GET/模型/云调用。

## 安全前提与证明

v1严格限定明确caption-repair失败child的subtitle.fetch/yt-dlp/modelNULL/current-v2已知completion持久化失败（原error精确LOCAL_RESOURCE，message精确“subtitle files were saved but stage persistence failed”），没有活跃或过期未澄清lease/owner、无response/finished/usage/cost、无任何dispatch或状态不明执行；旧Job必须FAILED_FINAL，全部attempt已明确终结且UTC时间/计数正规解析，run/job SHA关系唯一。正规解析全字段，禁止只查status。证明同源同Content真实成功后继、当前verifiedtimed/currentSummary/完整Evidence及providerresponse绑定，并证明旧输入/请求政策精确身份；仅前缀或时间先后不够。

旧capture仅承诺输入hash，未保存可逆语言顺序/provider版本等；允许从有限明确支持的冻结profile提出候选，但必须重算old raw-request hash、capture ID和全部身份完全匹配，不能把当前可变配置当原值。严格有界、canonical编码的proof_json及其SHA必须保存已验证语言序列、provider版本、refresh、来源metadata、quality flags、profile版本与所有关联ID，并与23字段一致。created_at是现在归档时间，不伪装完成前的历史捕获。

只由该旧任务已经pre-stage捕获的真实raw（预存hash、文件bytes与所有权都一致），使用明确受支持的冻结normalization/quality版本，重算derived bytes/path/hash与原canonicalrequest身份；旧派生文件逐字节匹配才能作为非权威retained DATA。缺旧输入快照、语言/版本/父子关系无法严格重建、关联不唯一均保持阻塞，不猜测，不把对未知文件当前自算hash当证明。全批检查后原子执行，任何失败整批不变。

未来同类任务可以在写derived文件前追加同表的严格owned证明（只在同scope真实raw和request身份已固定且无authority提升时），但任何newcompletion前持久化须维持liveowner/lease/CAS、transactionrollback无Evidence/成功。为避免该审批扩大范围，本提案初版只处理可完整证明的已失败且同源后继成功记录；未来无后继或待执行任务归档仍需另提精确增补，不自动实施。

## Backup/Restore精确修改与兼容

Backup文件集合合并普通Artifact与中性归档引用；保留原安全路径、无symlink/regularfile、大小/总量/磁盘/解压防攻击/hash校验。归档只作为retained DATA，schema38每个data_files record精确为relative_path、sha256、size_bytes、artifacts、retained_subtitle_derivations。后者是排序唯一的archive_id/proof_version/video_id/proof_sha256 references；普通artifacts原结构不改。每file至少一类引用非空，两类同path必须同hash/size，表行与refs严格完整coverage，不接受额外/缺失/重复refs。counts原data_artifacts仍只计普通Artifact引用，另增retained_derivations计归档引用；data_bytes按不同physicalpath只计一次，不把归档授为普通Artifact。旧34–37 record/count形状保持原契约不新增键。create/readiness增加live DATA全集与可验证索引集合精确匹配，任何未知额外file明确阻塞，不静默丢弃；不绕quiescence或放行其他Jobs/checkpoints/providerexecution。

schema34/35/36/37旧备份继续支持：旧manifest没有归档分支，按旧契约校验；正常restore后迁移追加空表。必须显式保留37，不能将LATEST=38后从supportedset漏掉37。schema38包在旧程序明确拒绝，不向后伪兼容。新包在新程序先校验表proof、所有文件、普通authority与中性proof分离，再stage/confirm/restart；恢复后已终止ledger不重新调用，归档文件无authority。归档准入时必须current后继Summary/Evidence仍一致；其后的Backup/Restore验证已绑定历史successor Job/request/Artifact/Evidence，不再要求未来current pointer永远指向它，避免正常refresh后阻塞。

迁移仅transactionalCREATE table/triggers/index+userversion，失败整事务回滚，不破坏旧数据。不可用旧程序直接打开已迁移库；回退使用迁移前完整备份和原程序，不做删表/降版本/数据reset。正式owner不参与测试，正式采用仍需最终另批。

## 文件范围与必须验收

state.py、transcripts.py仅精确失败proof/recovery接口、runtime_composition.py正常idlemaintenance调用、backup_restore.py、migration038与现迁移登记、对应integration/unit测试、task/handoff/中文手册。API/UI仅如需要readiness原因表达先报告，不改凭据/授权/模型/云配置、依赖、资格、rolling归一化或产品范围。实现与LOCALstate改动串行整合并独立审查。

真实隔离普通API/worker事务注入：失败→明确新child→真实后继成功→安全终止/归档→Backup readiness→实际GUI创建下载preview/RESTORE/重启→所有表和全部DATA路径/bytes/hash一致。并发启动/restore、unknown/PENDING/lease/response/Cloud/usage、时间/计数异常、错source/policy/后继、raw/derived改合法字节、未知file、混合批次、transaction回滚、重启/重复操作、旧schema34–37与新38恢复全负控；不删除/弱化原测试。全Backend/Frontend/TS/build/Ruff/strictmypy/diff及独立审查。

## 风险与批准依据

这是敏感的持久化/Backup契约及schema变更，最主要风险是错误退休、归档被当权威、漏文件/兼容旧包失败；精确proof、不可变独立表、完整全集验证与并发/旧新恢复检查控制。无法证明的旧文件仍阻塞，不能承诺所有历史状态都可自动修复。用户全局AGENTS及仓库AGENTS§5明确要求Schema及安全敏感改动先获具体批准；此前只批raw capture和v1/429，不能替代本范围授权。

独立只读提案预审（/root/intel_bounded_review，2026-10-13）：上述细节修订后可提交具体审批。使用原隔离fixture失败库已唯一重算captured VTT→raw request/capture ID→canonicalrequest/path/quality/148字节精确匹配，说明中性deterministic proof可行；该fixture provider不符合真实yt-dlp准入白名单，不能声称所有真实旧orphan已可自动修复。没有DDL/迁移/业务修改。
