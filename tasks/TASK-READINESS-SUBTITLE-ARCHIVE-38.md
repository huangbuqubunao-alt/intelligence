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

## 2026-10-14 第二次独立REJECT后的原作者返修包

Base61f740250872c67131a06d73eb93df86d202fd32，原tree readiness-subtitle-archive-38/原branch/原作者caption_resume，Reviewer intel_bounded_review。4f80后继proof修复有效但未接受整合；同一old failed child正规字段及历史snapshot仍缺，准确反证与ZipInfo/WAL复核见独立handoff。原审批覆盖Job/全部attempt/provider/source-run全字段正规计数/UTC/terminal证明，此返修继续同23字段Schema38/原安全范围，不重新申请迁移。

补齐old Job（包括max_attempts正规整数）、全部attempt与最终明确FAILED_FINAL、owner/lease与UTC全时序、正规SourceRun identity/state/不可变事件链；全部original_execution字段绑定既有canonical proof_json与exact-key/hash/history读取。live准入、幂等、历史readiness与Restore统一重验，不允许仍合法但已漂移字段。旧未发布incomplete38 proof保持closed，不修改不可变历史/升级旧proof。后继完整snapshot正控保留，未来合法current Summary切换仍通过，old34–37合同完全不变。

P2测试修正必须保留原ZipInfo/regular attrs，私有tamper DB保证WAL真正checkpoint后再封包/hash重算，并断言拒绝明确来自Neutral retention proof校验，不能把specialfile或DBhash提前拒绝称proof测试；保留旧断言，不删除/skip弱化任何负控。五old反证、两历史合法字段漂移、bad appended event/混合批次/rawfile全集/cancel/restorelease/幂等/未来pointer全部有真实外部观察，无新GET/模型。

caption成功completion当前复用fetch入口now，capture却用IO后真实clock；原CAPTION_REPAIR_PROPOSAL要求active owner/lease/CAS。本任务只准最小同caption repair完成边界使用当前实际clock验证持久化/lease与终结UTC，不准用旧时间延长租约、倒填历史或放宽proof，不改普通非repair pipeline广泛clock、不新增retry/reclaim/response权限。先复现delay越lease、owner改变与clock后退负控，检查实际同repair成功/失败记录时间能满足安全proof。若需新增持久化边界/Schema/其他模块权限，先停报告具体增补，不能夹带。

仅原transcripts.py/state.py及新增archive tests、精确caption tests与handoff，若其他路径先报告。先语法/TS不涉前端、TDD原候选反证、focused各旧新测试/static/diff提交STOP→独立重审。此次不重复19分钟旧完整backend；最终root接受整合后必须完整最新backend/front/TSbuild/GUI，旧4310+1FAIL保留。Parallel now独立UI已提交STOP的Reviewer（不业务写）；waiting核心接受后LOCAL_TEXT。所有正式服务/数据/模型/Cloud/依赖不动。
