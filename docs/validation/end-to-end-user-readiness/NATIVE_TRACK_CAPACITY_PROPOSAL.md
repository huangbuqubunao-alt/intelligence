# 原生字幕目录容量的精确隔离修复提案

2026-10-14，待具体批准；尚未修改provider代码。用户全链路实测发现真实后台关注后新发布的OYp5j2RihPE已正确发现/入库，但TRANSCRIPT终结INVALID_RESPONSE，真实页面没有字幕/Summary/Evidence。一次正确序列化的实际只读目录探针确认：`subtitle track directory exceeds its supported track limit`。探针先前一次在获取后错误用dataclass序列化Pydantic metadata，失败原证据保留；修正诊断不改变产品。

根因：providers/subtitles.py `_map_directory`把全部机器翻译`tlang`衍生轨道先计入1024个supported track限额并保存，最后enumerate_tracks才排除它们。即使真正原生轨道很少，大量本来不允许拥有Original Transcript权威的翻译轨道仍耗尽原生候选容量。512语言桶与4096目录entry总限额本身不是本修复扩容对象。

请求范围：仅在独立候选修改providers/subtitles.py `_map_directory`中已充分校验后的候选保留判定和必要私有helper，以及对应provider unit测试/最小integration、任务/handoff/手册。继续对每个entry（包括翻译）检查桶、结构、语言、ext、URL类型/长度/HTTPS/可信host/无凭据/无fragment、name及原4096entry上限；只有通过全部校验、支持现格式且没有精确`tlang`query key的原生候选才计入/保留在既有1024supported限额。真正原生超过1024仍failclosed，超过4096raw/512桶及任何恶意翻译结构/URL仍拒绝；不因被排除而跳过安全验证。原provider_position、轨道优先级、原有精确tlang排除语义、原生正文/规范化/hash/CAS/ledger/备份规则保持。

不增加网络请求或回退，不获取翻译正文，不改URL/语言/源metadata、不下载媒体、不读Cookie/凭据、不升级yt-dlp或依赖，不改Schema、配置/正式数据、模型资格/Cloud、重试与Job生命周期。现真实失败历史保留；仅本provider候选目录算法可先用原真实目录的显式捕获回放及严格负控证明，真实普通新导入/处理验收由root在隔离新数据执行且标注外部429等失败。老FAILED_FINAL如何普通用户重试若现合法入口不支持，另给精确方案，不借此改持久化。

先TDD：1024+合法翻译、少量原生应返回完整原生；1025原生/4097entry/513桶仍拒绝；翻译非法host/凭据/fragment/缺字段/坏name不能因排除而放行；tlang空值/重复key按现精确语义排除，普通非tlang query保留原签名；位置/格式/原身份/零翻译bodyreads稳定。既有完整provider及subtitle policy、nativecapture与Backup相关回归/static/diff和独立Reviewer。全部历史失败保留，不删除/skip/弱化测试或上限。

风险及审批：provider目录校验属于全局AGENTS“security-sensitive code”，且旧caption任务明确排除provider security transport，不能从通用继续授权推断扩文件范围。本提案只请求上述已验证entry保留点的隔离修复/验收；不授权正式采用或后续其他问题。DIRECT现标准库parse_qsl/urlsplit和provider validators；不新组件/依赖。
