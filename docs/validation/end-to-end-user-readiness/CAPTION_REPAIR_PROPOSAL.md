# 已完成但无时间轴字幕的安全补全范围

目的：普通导入已经记录 plain transcript 成功，但来源 JSON3 没有可验证时间轴，页面无法继续摘要和 Evidence。原生 VTT 已离线证明同一真实来源可提供严格原生时间轴；不得改造/裁剪 JSON3 时间或伪造旧任务失败。

已授权安全切片：同源/同语言/同轨道的有界原生格式回退，429/未知错误仍传播；新缓存版本；重启从哈希核验后的原生 raw 重新建立其真实时间轴，原始文件和历史不删。

请求的精确额外范围：在 state.py 增加一个仅用于明确用户重试的原子字幕补全方法（无 Schema migration）。现有 complete_stage 不允许 TRANSCRIPT_READY→TRANSCRIPT_READY，complete_job 禁止独立完成视频阶段任务，均保持原规则。新方法只接纳新的 repair child、当前用户创建 Source Run、active job owner/lease、当前视频恰为 TRANSCRIPT_READY、对应原始 subtitle/provider ledger/artifact 和经过严格原生时间轴/精确文本绑定的 canonical 数据；事务内验证成员关系、hash 和 expected current pointers，再一次性持久化新的 artifacts/provider completion/timed transcript/Evidence 与 repair child completion。视频状态及历史成功 Job 不回退、不伪改。当前已有可信 time/Evidence 的内容幂等返回，不重新获取或执行模型。

拒绝/恢复：未知 provider 状态、错误 owner/lease、外来/改动 artifact、不合法时间、冲突 current pointer、非允许 stage 均拒绝；并发只能由现有 Source Run/Job 唯一性与 Backup protected gate 正常准入。事务失败不留半完成 authority；重启恢复同一新的 command/job identity，不额外 model invocation。仍须独立代码审查及真实 GUI/重启/BackupRestore。

不涉及：Schema、凭据、模型/依赖下载、云费用、正式配置/owner DB/DATA/Vault、安全检查绕过、历史删除、把未完成任务当成功。实现仅在独立 captions worktree；main/正式采用仍另需最终具体批准。

风险：这是对字幕 authority 持久化边界的增补，属于用户全局 AGENTS.md “security-sensitive code” 需明确批准的范围。审批不表示代码或生产已通过；至少需要原生真实来源、错误/竞态/恢复/历史保留回归及独立 reviewer。

2026-10-12 用户已明确回复：“批准该精确隔离补全范围，继续验收”。本精确隔离实现范围已获批准；正式采用仍待全部验收及具体最终批准。
