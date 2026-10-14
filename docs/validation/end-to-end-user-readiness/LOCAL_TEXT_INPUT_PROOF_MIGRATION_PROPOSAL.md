# LOCAL_TEXT 输入历史证明：Schema 38→39 精确隔离迁移提案

2026-10-14，待具体批准，未实施。b79b509独立REJECT3b562c6发现两P1：合法摘要刷新后仅损坏原摘要文件，五可信入口仍接受；卡片缺失时current读取/保存/主题跳过新验证。Schema38没有原摘要、完整原输入/context投影字段。512字符execution ID不能通用承载原显示元数据、政策、preferences等；不压缩塞ID、不复用无关表、不枚举猜hash。

## 精确迁移

仅新增 `local_text_input_proofs`，15字段，不重建或改写既有表/记录：

| 字段 | 约束 |
|---|---|
| execution_id | PK、FK→distillation_execution_checkpoints.execution_id |
| proof_version | 固定local-text-input-proof-v1 |
| wire_version | 固定local-text-distillation-v2 |
| source_id | FK→source_subscriptions.source_id |
| video_id | FK→content_source_snapshots.content_id；校验同LOCAL TEXT及来源 |
| original_summary_artifact_id | FK→artifacts.artifact_id |
| global_policy_revision_id | FK→source_policy_revisions.revision_id，限定GLOBAL |
| source_policy_revision_id | 可NULL，FK同上，非NULL限定该SOURCE |
| input_json/context_json | 固定键/类型/canonical JSON，合计UTF-8≤512KiB |
| input_hash/context_hash/profile_hash/proof_hash | 各64位小写SHA256，proof_hash覆盖全部原投影和行身份 |
| created_at | 严格UTC |

除source_policy_revision_id外均NOT NULL。追加UPDATE/DELETE禁止triggers；INSERT检查checkpoint/source/Content/原Summary当前指针、明确MANUAL_CONTENT/local-only/零调用状态，json_each验证原Evidence/preference ID指向真实记录。只有必要source/video查找索引与现迁移登记/userversion39，不新增DATA文件，不授Transcript/Evidence/Intelligence或模型资格权威。Row存在不意味着已执行/成功。

## 输入与可信恢复

input保存完整原sealed projection：显示元数据、语言、全部引用/摘录/真实范围/hash、preferences身份/内容、global/source policy及实际规则/style、精确profile/model/digest/参数。context保存原snapshot/canonical身份、原Summary ID/hash/language/原引用集合及producer/reconstruction版本。沿用现20条Evidence及现preferences/rules/字符串上限；超限拒绝不截断。只使用真实现记录，不伪造hash/来源。

reservation在同一BEGIN IMMEDIATE验证当前事实并创建checkpoint+proof，先于任何dispatch claim；失败全回滚。入卡/NO_NEW保留当前CAS/预算/授权/未知状态规则。历史验证从指定原Summary字节/hash和原引用重构原deterministic result/requesthash，再复算完整input/context，而非当前presentation集合。合法后续刷新可读，原文件/引用/投影损坏必须closed。显式v2由持久版本/关联分类，缺proof/card/ledger均拒五入口，不能降级generic；原YT/timed、无提炼关联的generic非card不改。旧未发布b79格式不倒填或自动升级。

## 旧数据、备份与风险

明确旧34–38包先按原合同验包，再只在隔离恢复候选添加空39表；旧表与全部DATA不变，不补造历史输入。新39包必须验证每份proof身份/hash/外键/历史来源，包含取消/NO_NEW/正向/未知执行恢复；不绕Backup。旧程序不接受39，失败候选保留且正式不迁移；没有反向删除迁移，采用与回退安排另行具体批准。风险是输入证明被错误授权、历史重构破坏合法刷新或遗漏恢复校验，须两原反证/混合批次回滚/幂等/并发/取消重启/旧新全表全DATA测试及独立Reviewer。

新增允许范围仅039 migration、state.py登记/原子proof、distillation.py/已批prepare freeze、intelligence_read.py必要历史helper/read_current、backup_restore.py proof与39支持、runtime.py doctor最新版本及对应测试/任务/handoff/docs。runtime_composition/provider/UI/deps/config/credentials/正式owner/Cloud/模型资格不改。本轮真实模型0调用，原四例FAIL/LOCAL8仍BLOCKED，Schema批准不授权任何推理或正式采用。

Reuse DIRECT现SQLite/protected gate/restore lock/SourceAuthority/Evidence/Summary/hash/profile/backup机制；新表仅必要历史事实，避免错误字段承载。全局AGENTS与仓库AGENTS§5要求Schema/安全敏感持久化边界具体批准，原LOCAL_TEXT无Schema授权，故本步骤先暂停，其他已批UI及检查继续。

## 2026-10-15 用户具体批准

用户回答：**“批准该精确隔离迁移与验收范围”**，对应问题 call_37d985304ad94a94b581ed1e53765c44。仅授权本文15字段、隔离39迁移/旧新恢复及两P1修复；不授权正式采用或任何真实模型调用。
