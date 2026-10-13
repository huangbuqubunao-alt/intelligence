# LOCAL_TEXT 已批补全：可信读取文件范围补充

2026-10-14，待具体批准，未实现。原 LOCAL_INTELLIGENCE_CHAIN_PROPOSAL.md 两切片已批准；LOCAL_TIMED已接受，LOCAL_TEXT仍等待Schema38核心接受。新增真实模型验收仍因原四例未通过而禁止，本补充不改变该前提。

只读预检确认现 intelligence_read.py 的 AuthoritativeIntelligenceReader._read_card 是保存、主题和读取使用的可信边界，其 canonical card hash 只包含 evidence_id/start_ms/end_ms/stance。原获批文本引用须绑定真实 TEXT_RANGE locator/Unicode码点半开offset/行号/source、canonical、excerpt hash，timestamps必须NULL；写入新显式范围而不更新可信读取将导致新卡 CARD_HASH_INVALID。绕过reader或伪造时间均不可采用。

请求仅将 src/youtube_intel/intelligence_read.py 的 _read_card 及必要的私有精确验证helper加入已批LOCAL_TEXT文件范围，并追加对应integration/unit tests。按已批新LOCAL_TEXT版本化输入/输出/持久化hash契约验证真正文字范围；使用现有 Evidence/source_authority resolver、应用sealed input和执行关联证明，重新绑定同Content、当前/记录revision合法性、source/canonical/excerpt hash、真实码点范围及派生行号，不靠外部URL参数或模型字段授范围authority。所有存储字段复用现Schema，不改Schema、历史记录、保存/主题CAS或失效规则。

新版本分支必须由可验证的持久化版本/执行关联明确区分，不能尝试多个hash择一通过或仅凭NULL时间推断新资格；旧YouTube v5与旧卡canonical/hash字节、读取行为保持原合同。不接受混合TIMED/TEXT、错版本、缺执行关联、损坏或非当前可信范围、伪0ms、跨Content或改变hash。若现存Schema不能明确承载上述版本与关联，先停并报告，不自行迁移或降低校验。

原 approved distillation.py/state.py/local_api.py/runtime_composition必要接入/frontend Evidence范围不扩到其他模块。独立task作者/Reviewer、精确wire冻结、正负控/旧YT及LOCAL Cloud零调用/NO_NEW coverage/保存主题引用/BackupRestore、完整回归均继续要求。schema38未独立接受前不写核心代码。真实9b后续资格与LOCAL八例仍不授权；无正式数据、配置、凭据、依赖、Cloud调用或发布。

批准原因：原提案没有列 intelligence_read.py，该文件属于用户全局AGENTS“security-sensitive code”及授权可信读取边界，需具体批准新增最小文件范围；不是重新要求批准此前LOCAL_TIMED/TEXT主体。本补充目的只让已批文本locator在同一可信reader验证，不授额外执行或权威。
