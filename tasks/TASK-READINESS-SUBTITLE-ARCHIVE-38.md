# TASK-READINESS-SUBTITLE-ARCHIVE-38

2026-10-13，READY。主控/root；Implementer /root/caption_resume；Reviewer /root/intel_bounded_review。依赖LOCAL_TIMED已独立APPROVE f399034d/17e3f8b，root整合3c4ee35/c90406e，78受影响测试PASS/43.95秒。新任务从本任务卡提交后的root最新基线创建，不沿旧RAW树开发。

批准：用户明确“批准该精确隔离迁移与验收范围”，见FAILED_SUBTITLE_ARCHIVE_APPROVAL.md及FAILED_SUBTITLE_ARCHIVE_MIGRATION_PROPOSAL.md。后者是精确实现合同，23字段和旧34–37/new38 manifest/proof分支不能简化。只隔离，未授权正式迁移/采用。

目标：已知current-v2 caption-repair completion持久化失败→明确新child真实成功后，严格证明旧任务无未知执行，原子保留非权威derived DATA/全部历史并安全终止旧ledger；原Backup保护不绕过、旧新包全表全DATA恢复一致。未知文件/历史身份不可证明继续阻塞，不能删除文件或当Transcript/Evidence/成功输出登记。

Allowed：state.py、transcripts.py仅精确proof/recovery接口、runtime_composition.py仅普通idlemaintenance、backup_restore.py、migration038/既有迁移登记、相应tests、本task/handoff。任何额外product文件先报告；API/UI仅必要readiness原因表达先报告。不改Cloud/资格/auth/依赖/配置/正式owner/rolling/容量/LOCAL TEXT。旧错误/attempt/available历史不变，只旧ledger status/finished_at/updated_at CAS，理由新不可变表；migration仅append table/triggers/index/userversion。

Reuse DIRECT：已批准schema migration机制、SQLite protected gate/BEGINIMMEDIATE、restore锁、captured raw/request/source-run所有权、严格provider状态、冻结normalization和hash/Source authority、既有Backup路径/限额/ZIP校验；REFERENCE获批提案/RAW handoff。REJECT unknown hash补登记、当前可变profile冒充旧输入、通配备份文件、归档被当普通Artifact、假零历史调用/假Success、丢manifest37支持。

先完整阅读提案并复述精确接口/文件、TDD真实边界。可复用只读fixture算法证据但其 controlled-subtitle-boundary provider不满足真实yt-dlp白名单；不得弱化白名单来让测试过。须构造明确真实adapter identity的隔离受控provider transport fault，保留before原失败。真实公网普通GUI成功路径由root最终验收；模型调用0、不下载、不付费、不读正式数据库/凭据/资格seal。

Required：approved所有known/unknown/concurrency/idempotence/restart/old34–37/new38/全表全DATA/authority分离/源和current后继CAS/未来refresh历史证明/计数UTC解析/混合batch回滚负控；先类型语法，focused+完整backend（现约4259+）、Ruff src/tests/scripts、strictmypy src、git diffcheck。Frontend若未改只复核由root全量；D2-01/02 relevant Backup/APFS限额回归。不删/skip/弱化tests或改test scripts，失败原证据保留。

提交有界commit和完整handoff后STOP，建议IN_REVIEW不自行DONE/main。有规格空白/需扩大scope先报root，无自动新增迁移/字段/既有表改写。主控整合检查后真macOS GUI backup/download/preview/RESTORE/restart，所有表与全部物理DATA逐字节相等才验收。

立即启动迁移。可并行：Keyboard已作者STOP，reviewer只审App/handoff不冲突；rootGUI/资料核验。等待：LOCAL_TEXT涉及state，必须本迁移接受整合后串行；9b真实FAIL/LOCAL8例仍BLOCKED，不授资格。
