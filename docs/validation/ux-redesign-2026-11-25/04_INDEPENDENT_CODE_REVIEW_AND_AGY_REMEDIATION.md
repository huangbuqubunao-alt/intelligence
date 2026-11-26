# Intelligence｜独立 Code Review 与 AGY 整改执行任务书

- 日期：2026-11-25
- 审查角色：Senior Staff Engineer + 产品总监（独立静态源码审查）
- 状态：**HOLD — 暂缓合并**
- 仓库：huangbuqubunao-alt/intelligence
- 审查分支：antigravity/task-user-readiness-20261112
- 审查 SHA：[e13cc28c0cadf5869e19d51b90c84bdcabc09655](https://github.com/huangbuqubunao-alt/intelligence/commit/e13cc28c0cadf5869e19d51b90c84bdcabc09655)
- 对照 main：[d1b58f731adc4185fe78cc5538e9e211b8a0e211](https://github.com/huangbuqubunao-alt/intelligence/commit/d1b58f731adc4185fe78cc5538e9e211b8a0e211)
- 共同祖先：cdb3bf6e54917d744f079c3732f5e8c853471535
- [GitHub Compare](https://github.com/huangbuqubunao-alt/intelligence/compare/main...antigravity/task-user-readiness-20261112)：diverged，任务分支 ahead 116 / behind 101。以上为审查时快照，不代表当前实时状态。

> 本文同时是独立审查记录与 Antigravity（AGY）执行规范。禁止把它当成已运行测试的验收报告。所有源码链接固定在审查 SHA；后续发现行号变化，按符号定位。流程图是根据源码和建议绘制的示意，不是实机截图。原验收报告引用的本机截图未由独立 Reviewer 获取，不能伪造附图。

## 1. 合入结论与优先级

**暂缓合并 main。** 未证实 P0 灾难性漏洞；7 项 P1 合入阻断/验收缺口，5 项 P2 改进项。P1 全部闭环且集成验证通过后重新独立审查；不允许自动合入 main。

| 维度 | 独立静态评价（主观，非实测） | 结论 |
|---|---:|---|
| 产品体验 | 76/100 | 阅读结构与异常恢复明显改进 |
| 前端工程与可维护性 | 65/100 | 抽屉无障碍缺陷，组件过大 |
| 后端与安全 | 68/100 | 默认 BYOK 防护较好，媒体/授权/证据边界尚未闭环 |
| 可合入性 | 40/100 | 双向分叉，缺少当前集成结果验证 |
| 等权综合 | 62.25/100 | HOLD |

AGY 自评 UX 64→92 分与上述四维审查不属于相同口径，不可直接当成统计测量；92 分不能证明商业化或合入就绪。

### 审查边界
实际读取任务分支九份指定源码/测试及其 main 对应文件（main 不存在 ManualUxRemediation.test.tsx）、三份 UX 报告和相关授权、字幕、运行时及 state 源码。未 checkout、运行构建/测试、验证真实浏览器或核查所有 217 个独有提交。GitHub Compare 文件清单有返回范围限制。当前提交 combined status 为空、查询到的 PR 类型 workflow runs 为空；这不是 CI 失败证据，也不是 CI 通过证据。

## 2. P1 合入阻断清单（每项先建立复现或反证）

### P1-01｜本地媒体读取缺少统一 Host 信任边界
- 证据：[src/youtube_intel/local_api.py:4220–4270](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/local_api.py#L4220-L4270)（_handle），[src/youtube_intel/local_api.py:4398](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/local_api.py#L4398)（loopback bind）。
- 实际：native 路由检查 Host/Origin/请求头，但普通 GET/HEAD 进入 backup_download 前没有同样的 Host 白名单；main 已有类似缺口，新媒体端点扩大暴露面。
- 复现：在隔离工作区导入假视频，用不属于本地应用的 Host 发起读取，断言拒绝；浏览器 DNS rebinding 的可利用性尚未实测，不得直接宣称远程漏洞。
- 影响：本地隐私读取边界不完整。
- 修复：统一 Host allowlist 与跨站读取策略，考虑 CORP same-origin；兼容 localhost/127.0.0.1、真实应用启动与 HTML5 媒体读取，拒绝不可信 Host；检查所有读取接口而非只修 media。
- 验收：非法 Host、跨站、合法本机读取、正常 Range 均有真实 HTTP 测试；不得牺牲现有桌面桥安全契约。

### P1-02｜媒体读取未保留受管根目录信任链
- 证据：[src/youtube_intel/fast_read_api.py:2044–2089](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/fast_read_api.py#L2044-L2089)（_resolve_local_media_file），[src/youtube_intel/local_api.py:4173–4177](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/local_api.py#L4173-L4177)（_send_file），[src/youtube_intel/source_authority.py:96–134](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/source_authority.py#L96-L134)（managed_directory/open_managed）。
- 实际：SQL 参数化、拒绝 ..、末端 symlink、resolve/is_relative_to、MIME 白名单已有。但返回 resolved 绝对路径后再 open_managed(path.parent,path.name)，丢失原始受管 root + relative path；原始快照哈希未在播放路径验证。
- 复现：隔离夹具中替换绑定后的存储根为指向测试目录的 symlink；测试中也覆盖父级 symlink、非法 storage_root、绝对路径、软链接替换和非媒体路径。需要本地存储被修改的前提，禁止描述为已证实任意远程读。
- 修复：保留受管根和规范相对路径，使用逐级 O_NOFOLLOW 的 open_managed；明确允许的 storage_root，不静默信任未知值。建立文件身份/完整性契约，避免每个 Range 全量哈希导致大文件卡顿；校验与读取应针对同一文件身份。
- 验收：所有逃逸夹具 fail-closed；合法视频完整读和 Range 保持正常；测试源被替换、读中被修改时不误报已验证。

### P1-03｜GROUNDED 只证明引用编号合法，不证明结论受原文支持
- 证据：[src/youtube_intel/workspace_intelligence_hub.py:897–960](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/workspace_intelligence_hub.py#L897-L960)（_prune_ungrounded_ref_clauses），[src/youtube_intel/workspace_intelligence_hub.py:7313–7398](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/workspace_intelligence_hub.py#L7313-L7398)（问答状态），[src/youtube_intel/workspace_intelligence_hub.py:7700–7800](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/workspace_intelligence_hub.py#L7700-L7800)（历史问答再验证）。
- 实际：后端验证 E<n> 标签、引用绑定和原文，但合法标签可能附在错误陈述上。
- 最小复现：真实 E1 = “收入同比增长 5%”；模型桩返回 answerable=true、合法 E1 和“收入同比增长 300% [E1]”。断言不得显示为已核实事实；同时测试数字、日期、否定、主体错配及无证据推断。
- 影响：直接损伤产品核心可信度。
- 修复：明确区分引用真实性、事实支持关系和模型推断；对关键数字/日期/金额等实施确定性一致性校验，无法验证则标为推断/未验证或拒答。保留原文证据链，处理历史会话、UI、导出与兼容迁移。不要仅加 prompt 或声称能形式化证明所有自然语言语义。
- 验收：矛盾断言不被标 GROUNDED/已核实；真实支持陈述仍可输出；无据拒答和旧会话状态回归通过。

~~~mermaid
flowchart TD
  A["模型回答"] --> B["引用编号与原文绑定验证"]
  B -->|失败| R["拒答 / 无有效证据"]
  B -->|通过| C["事实与证据支持关系校验"]
  C -->|明确矛盾| R
  C -->|不确定| U["明确标为推断或未验证"]
  C -->|支持| G["可核验的有依据陈述"]
~~~

### P1-04｜YouTube 授权频控存在检查与执行竞态
- 证据：[src/youtube_intel/youtube_auth_fallback.py:522–585](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/youtube_auth_fallback.py#L522-L585)（can_attempt/_record_usage），[src/youtube_intel/youtube_auth_fallback.py:671–739](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/youtube_auth_fallback.py#L671-L739)（attempt_authenticated_ingest），[src/youtube_intel/runtime_composition.py:302–315](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/runtime_composition.py#L302-L315)（兜底装配）。
- 实际：资格检查在锁内，网络调用在锁外，usage 在结束后写入；runtime 可能新建 service 实例，实例锁不能保证全局额度。
- 复现：假授权网络调用 + barrier；当日仅剩 1 次额度时并行两个 service，确保第一笔 usage 未写入前检查。生产 HTTP 调度是否能直接触发尚未实测。
- 修复：SQLite 事务内原子预留额度/冷却槽，执行后 finalization；崩溃后保守回收策略，跨线程/实例测试，断开授权和熔断状态也须一致。
- 验收：剩 1 次时最多 1 个调用发出；429/授权拒绝触发熔断，不自动扩大授权范围。

~~~mermaid
sequenceDiagram
  participant A as 请求 A
  participant B as 请求 B
  participant DB as SQLite
  A->>DB: 原子预留最后一个授权槽
  DB-->>A: 允许
  B->>DB: 尝试预留
  DB-->>B: 拒绝 / 冷却
  A->>A: 执行已授权采集
  A->>DB: 结算与记录结果
~~~

### P1-05｜右侧资料抽屉关闭时仍进入 Tab 焦点
- 证据：[frontend/src/workspace/App.tsx:6235–6260](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/App.tsx#L6235-L6260)、[frontend/src/workspace/App.tsx:7286–7330](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/App.tsx#L7286-L7330)（ContentDetailPanel），[frontend/src/workspace/styles.css:5816–5838](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/styles.css#L5816-L5838)。
- 实际：aside 始终挂载，仅 transform/opacity/pointer-events 隐藏；这些 CSS 不移除键盘焦点/无障碍树。关闭时多个 pane 仍为 reader-ref-pane。Escape 有实现但无完整焦点管理。
- 复现：详情页不打开抽屉，真实浏览器持续 Tab；打开后 Shift+Tab/Escape，再验证触发按钮焦点。
- 修复：独立 ReaderReferenceDrawer；使用成熟 Dialog 语义，关闭时 inert 或卸载，打开时迁移焦点，关闭后恢复触发按钮；若保留动画，保证动画期间隐藏语义正确；tab/tabpanel 建立关联，键盘导航符合语义。保留证据深链和加载/翻译状态，不因重构丢数据。
- 验收：Playwright/真实浏览器验证关闭状态无抽屉焦点、打开时焦点受控、Escape/点击遮罩后恢复、Evidence 深链定位；390px 双主题无溢出。

~~~mermaid
flowchart LR
  A["详情页：抽屉关闭"] --> B["点击原始资料 / 证据深链"]
  B --> C["抽屉打开：焦点进入"]
  C --> D["字幕 / 证据 / 处理记录"]
  D --> E["Escape / 关闭"]
  E --> F["抽屉 inert 或卸载，焦点恢复"]
  F --> A
~~~

### P1-06｜媒体不可用时静默断开、HEAD 错误响应需收口
- 证据：[src/youtube_intel/local_api.py:4173–4213](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/local_api.py#L4173-L4213)、[src/youtube_intel/local_api.py:4258–4270](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/local_api.py#L4258-L4270)、[src/youtube_intel/source_authority.py:121–134](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/source_authority.py#L121-L134)；[src/youtube_intel/local_api.py:4130–4142](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/local_api.py#L4130-L4142)（_send_bytes 无条件写正文）。
- 复现：快照替换为空文件或 >2 GiB 稀疏测试文件；测试不存在文件的 HEAD 和 Range 416。
- 影响：响应头发出前的 OSError/ValueError 被吞掉，客户端可能收到空连接；HEAD 经 _send_bytes 可能写正文。
- 修复：区分 headers 已发送与未发送；未发送时按契约返回 404/413/完整性错误，已发送时安全断流并记录脱敏诊断；统一 HEAD 不写正文。保留 1 MiB 分块与 2 GiB 上限。
- 验收：200/206/416、HEAD 成功/失败、空文件/超限/删除/读中变化全部有断言；不能以空连接代替预期错误码。

### P1-07｜验收报告不覆盖当前审查 HEAD，更未覆盖集成结果
- 证据：[docs/validation/ux-redesign-2026-11-25/03_ACCEPTANCE_AND_QUANTITATIVE_REPORT.md:3–20](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/docs/validation/ux-redesign-2026-11-25/03_ACCEPTANCE_AND_QUANTITATIVE_REPORT.md#L3-L20)、[frontend/src/workspace/ManualUxRemediation.test.tsx:959–1122](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/ManualUxRemediation.test.tsx#L959-L1122)。
- 实际：报告验证终点 902aa774，专项测试 11/11；e13cc28c 中有 13 个 it 声明，新增抽屉/播放器。当前 GitHub combined status 和 PR workflow runs 查询为空。
- 复现：核对报告 SHA、测试声明、GitHub 检查；不得推断当前测试通过或失败。
- 修复：先记录当前工作树、HEAD/main/merge-base，独立集成分支合并最新 main，人工审查冲突/安全变更/迁移/API 契约，运行完整测试并保存证据；更新报告绑定确切代码提交。文档提交与代码验证 SHA 区分。
- 验收：以集成代码 SHA 为准，提交真实命令、退出码、测试数量、日志、截图、失败与 NOT_TESTED 清单；最终由用户决定是否合入。

## 3. P2 改进（正式发布前完成；先验证范围，不得借机全盘重写）

| ID | 证据与问题 | 最小复现/影响 | 最小整改与验收 |
|---|---|---|---|
| P2-01 | [src/youtube_intel/local_api.py:4144–4171](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/local_api.py#L4144-L4171) _parse_byte_range：int 接受非标准数字、split 丢弃后续范围 | bytes=+4-19、bytes=0-5,10-15、非法/越界 Range；协议行为不明确，未发现整数溢出 | ASCII 数字严格解析，明确多范围处理策略，补齐后缀、开放尾、截断、416、HEAD 测试；遵循 HTTP 语义 |
| P2-02 | [src/youtube_intel/youtube_auth_fallback.py:120–154](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/youtube_auth_fallback.py#L120-L154)、[src/youtube_intel/youtube_auth_fallback.py:588–657](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/youtube_auth_fallback.py#L588-L657)：Cookie 验证只需至少一个允许域，原样保存其他行 | 假 Cookie 文件混入无关站点；凭据持有范围扩大，不等同于已证实外传 | 域名精确边界与最小必要 Cookie 过滤；明确浏览器授权范围；假凭据测试与导出扫描 |
| P2-03 | [frontend/src/workspace/WorkspaceAiWidgets.tsx:3999–4038](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/WorkspaceAiWidgets.tsx#L3999-L4038)、[src/youtube_intel/workspace_intelligence_hub.py:6882–6930](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/workspace_intelligence_hub.py#L6882-L6930)：候选资料计数被描述成全库可核验资料 | 修改本地媒体源但保留转写 cue，可能仍计入候选；回答实际拒答 | 显示“候选资料 N 篇”；回答后展示实际覆盖、有效证据及拒答原因 |
| P2-04 | [frontend/src/workspace/App.tsx:6497–6557](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/App.tsx#L6497-L6557)：所有播放错误归并为读取失败 | 浏览器不支持编码时同样报错，易误以为文件丢失 | MediaError.code 分类，明确重试或本机播放器等可用替代路径；测试不同错误 |
| P2-05 | [frontend/src/workspace/App.tsx:6182–7417](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/App.tsx#L6182-L7417)、[frontend/src/workspace/WorkspaceAiWidgets.tsx:3999–4042](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/WorkspaceAiWidgets.tsx#L3999-L4042)：大型组件状态混杂、范围提示重复构造 | 修改播放器或抽屉需动大型组件，回归成本高 | 小批拆分 ReaderMediaStage、ReaderReferenceDrawer、ReaderSynthesis、ReaderRecoveryPanel、useReaderState；ResearchScopeReadout/VaultBackupPanel 仅在契约稳定后拆分；不做无必要重写 |

文件规模（文本行数含空行）：App.tsx main 10198 → 10833；WorkspaceAiWidgets.tsx 4993 → 6139；styles.css 5299 → 5868。行数不是单独判定 Bug 的依据。

## 4. 正向证据与必须保留的契约

| 范围 | 已有源码证据 | 待验证 |
|---|---|---|
| 本地媒体 | [src/youtube_intel/fast_read_api.py:2044–2122](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/fast_read_api.py#L2044-L2122) 参数化、路径边界、MIME；[src/youtube_intel/local_api.py:4173–4213](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/local_api.py#L4173-L4213) 1 MiB 分块与限制；[src/youtube_intel/source_authority.py:28–30](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/source_authority.py#L28-L30) 2 GiB 上限 | P1-01/02/06 及 Range 测试 |
| CSP | [src/youtube_intel/local_api.py:4010–4015](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/local_api.py#L4010-L4015) media-src 'self' blob:，connect-src 'self' | 双主题实际播放器、安全响应头；不得放宽到任意远程 |
| 默认 BYOK | [src/youtube_intel/workspace_intelligence_hub.py:362–430](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/workspace_intelligence_hub.py#L362-L430) URL 验证；[src/youtube_intel/workspace_intelligence_hub.py:456–600](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/workspace_intelligence_hub.py#L456-L600) DNS 校验、固定公网 IP、TLS；[src/youtube_intel/workspace_intelligence_hub.py:1752–1764](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/workspace_intelligence_hub.py#L1752-L1764) 禁代理/重定向默认 opener | [src/youtube_intel/workspace_intelligence_hub.py:1817–1842](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/workspace_intelligence_hub.py#L1817-L1842) 自定义 opener 是否只用于受信任测试装配；DNS 混合地址、重定向、代理与日志验证 |
| YouTube 授权 | [src/youtube_intel/youtube_auth_fallback.py:157–182](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/youtube_auth_fallback.py#L157-L182) HTTPS/域名重定向限制；[src/youtube_intel/providers/subtitles.py:744–773](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/providers/subtitles.py#L744-L773) 初始字幕 URL 限制；[src/youtube_intel/youtube_auth_fallback.py:363–382](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/youtube_auth_fallback.py#L363-L382) 安全状态投影；[src/youtube_intel/youtube_auth_fallback.py:588–657](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/youtube_auth_fallback.py#L588-L657) 临时文件 0600 | 系统代理与 yt-dlp 不等同 BYOK DNS pinning；验证 DNS/重定向信任边界，禁止凭空承诺全链路 SSRF 绝对安全 |
| 凭据隔离 | [src/youtube_intel/workspace_intelligence_hub.py:2191–2217](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/workspace_intelligence_hub.py#L2191-L2217) GET 不返回 Key；[src/youtube_intel/workspace_intelligence_hub.py:9680–9692](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/workspace_intelligence_hub.py#L9680-L9692) 导出引擎配置字段白名单 | 所有备份/ZIP/导出/异常日志/历史数据的假凭据扫描；不得读取真实 Cookie 或发送真实付费请求 |
| 证据缓存 | [src/youtube_intel/workspace_intelligence_hub.py:6350–6381](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/workspace_intelligence_hub.py#L6350-L6381) LOCAL/BILIBILI 不跨请求缓存；[src/youtube_intel/state.py:8304–8315](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/state.py#L8304-L8315) 本地来源重新权威验证；[src/youtube_intel/fast_read_api.py:1959–2010](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/fast_read_api.py#L1959-L2010) 外层数据根指纹，[src/youtube_intel/fast_read_api.py:234–347](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/src/youtube_intel/fast_read_api.py#L234-L347) 内容/文件属性指纹 | 热缓存形成后修改/删除/替换真实磁盘夹具，HTTP 重读必须降级；未证实已有缓存漏洞 |
| 首页 | [frontend/src/workspace/App.tsx:2053–2062](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/App.tsx#L2053-L2062) Dashboard 在 KnowledgeDelta 前 | 保留周报/快速开始优先 |
| 去重 | [frontend/src/workspace/App.tsx:4764–4776](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/App.tsx#L4764-L4776) manualPendingIds 过滤 | 搜索、来源筛选、恢复后更新一致 |
| 授权返回 | [frontend/src/workspace/WorkspaceAiWidgets.tsx:5804–5811](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/WorkspaceAiWidgets.tsx#L5804-L5811) 受限内部 Hash | 返回、取消、重试、并发状态测试 |
| 设置 | [frontend/src/workspace/WorkspaceAiWidgets.tsx:5525–5565](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/WorkspaceAiWidgets.tsx#L5525-L5565) Vault 独立区域；[frontend/src/workspace/WorkspaceAiWidgets.tsx:3999–4038](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/WorkspaceAiWidgets.tsx#L3999-L4038) 范围提示 | 解释导出与快照区别，编辑模型时保持可达 |
| CSS | [frontend/src/workspace/styles.css:5816–5866](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/styles.css#L5816-L5866) 语义 token、94vw；[frontend/src/workspace/styles.css:2760–2765](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/styles.css#L2760-L2765) reduced motion | 390px 详情抽屉/长文本/深浅主题真实浏览器与对比度；重复 selector 若为响应式覆盖不应误判 |

## 5. 测试与三份 UX 文档可信度

### 前端
[frontend/src/workspace/ManualUxRemediation.test.tsx:1044–1069](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/ManualUxRemediation.test.tsx#L1044-L1069) 只检查 is-open、aria-selected、Escape 和深链，不证明 Tab 焦点与真实滚动；[frontend/src/workspace/ManualUxRemediation.test.tsx:1115–1121](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/frontend/src/workspace/ManualUxRemediation.test.tsx#L1115-L1121) 只断言 video 和 src，不证明解码/播放/seek。现有 Mock 用于契约和状态机测试有价值，不能代替浏览器端到端验证。

### 后端
[tests/integration/test_local_video_post_import_resilience.py:566–616](https://github.com/huangbuqubunao-alt/intelligence/blob/e13cc28c0cadf5869e19d51b90c84bdcabc09655/tests/integration/test_local_video_post_import_resilience.py#L566-L616) 启动真实 loopback HTTP，覆盖完整 200、指定 206、非媒体 404；未在该专项用例中覆盖 HEAD、416、非法 Host、symlink、超限、读中修改、浏览器播放。不要把未覆盖误写成全仓库必然无测试，先查全库既有测试再补缺。

### 报告
- [01_UX_AUDIT_AND_MARKET_RESEARCH.md](01_UX_AUDIT_AND_MARKET_RESEARCH.md)：基线步骤/交互节点和模拟画像有用，竞品“高频痛点”证据样本不足；不代表真实用户需求统计。
- [02_IA_FLOWS_COPY_AND_DESIGN_SYSTEM.md](02_IA_FLOWS_COPY_AND_DESIGN_SYSTEM.md)：设计分层、文案与主题规范基本合理，焦点迁移与状态覆盖未完全落实。
- [03_ACCEPTANCE_AND_QUANTITATIVE_REPORT.md](03_ACCEPTANCE_AND_QUANTITATIVE_REPORT.md)：旧 SHA 报告；真实云端与真实 Cookie 明确 NOT_TESTED 值得保留，92 分及“100% 布局缺陷消除”不可外推。9/10 无障碍分未反映最新抽屉缺陷。模拟 persona 不是外部真人实验。
- 独立 Reviewer 未获取报告中本地绝对路径的原始截图，AGY 应在本机重拍、归档到仓库可审阅路径；不得生成假的实机截图或将示意图标成截图。

## 6. 产品体验 Top 3（优先解决任务闭环，而不是增加功能）

### TOP 1｜授权恢复就地完成
保留明确同意与权限说明，不自动读取 Cookie。当前：详情 → 设置 → 选择浏览器/保存 → 返回 → 重试。建议：受阻视频详情提供轻量授权入口，用户确认后继续当前视频的采集并展示进度、失败及取消选项。高级设置留在 Settings。严禁绕开网站验证或静默授权。

~~~mermaid
flowchart TD
  subgraph Before["当前：跨页面恢复"]
    B1["视频受阻"] --> B2["打开设置"] --> B3["选择浏览器并保存"] --> B4["返回原视频"] --> B5["手动重试"]
  end
  subgraph After["建议：当前任务内恢复"]
    A1["视频受阻"] --> A2["解释原因与授权范围"]
    A2 --> A3["用户明确同意并重试"]
    A3 --> A4["显示进度 / 成功 / 可恢复失败"]
    A2 --> A5["取消或保持匿名"]
  end
~~~

### TOP 2｜阅读器以决策为中心
保留媒体、摘要、证据与历史，默认优先回答“值不值得看 / 不看原视频能获得什么 / 能做什么 / 依据在哪”。已有评分可使用但说明其性质，不得新增未经验证的阅读时间或客观置信度。字幕、证据、历史按需披露；减少重复总结、重复 CTA 和裸露诊断。下面为信息架构示意而非实机截图。

~~~mermaid
flowchart TD
  A["标题 / 原片时长 / 价值分级"] --> B["封面或本地播放器"]
  B --> C["30 秒看懂：核心归纳"]
  C --> D["关键观点 / 有依据的行动建议"]
  D --> E["标已读并继续下一篇"]
  D --> F["按需查阅"]
  F --> G["原始字幕"]
  F --> H["原话证据"]
  F --> I["处理记录"]
~~~

### TOP 3｜导航按用户任务解释
首页：今天值得关注什么；内容：管理和阅读已有资料；关注：持续跟踪来源；洞察：发现有价值观点；主题：观察长期脉络；AI 问答：直接向资料提问。让问答入口可发现，统一命名和文案。不得仅为了重新排版破坏原有路由、导航键盘契约和用户数据。先评估方案，再做最小可验证调整。

## 7. /goal — AGY 执行指令（本文即任务源）

唯一目标：将 Intelligence 当前任务分支安全集成到最新 main 基线，在保留已验证 UX 成果的前提下关闭 P1 与必要 P2，形成可审计、可复现、可独立复核的候选交付。不是无限制添加功能或大规模改写。

### 阶段 0：只读预检
- 自行定位本地项目、git remote、当前分支与工作树，核验本文件所在分支和最新 HEAD；原审查 SHA 不等于此文档提交 SHA。
- 先检查已有未提交改动、未推送提交和其他 agent 正在工作的分支；禁止 reset --hard、清理用户文件、覆盖或强推。
- fetch 最新 main 和任务分支，记录 SHA/merge-base/ahead-behind，列出完整变更与潜在冲突（数据库迁移、安全策略、API、桌面装配、前端路由、测试和依赖优先）。
- 建立独立集成/整改分支；优先通过可审计的 merge 方式保留双方有效改动，若发现不适合，记录方案比较与依据。不得直接操作 main，不得自行合并 PR。
- 生成阶段执行清单，逐条标明本次 findings 的 confirmed / disproved / already-fixed / needs-reproduction，必须附源码与测试证据。不要为了让清单变绿制造无意义修复。

### 阶段 1：集成与安全优先
- 集成 main，审查冲突，保证旧数据与迁移兼容，运行基线测试；若集成发现安全/数据 P0，停止有风险的动作并报告。
- P1-01/02/06：媒体边界、路径信任链、错误与 HEAD；P2-01 Range 同批收口。
- P1-04：授权频控原子性；P2-02 凭据最小化、Cookie/BYOK 安全验证与假凭据导出扫描。
- P1-03：证据状态真实性、矛盾断言与历史问答；验证外层/内层热缓存。P2-03 同批修正文案和计数口径。

### 阶段 2：UX 与工程
- P1-05：抽屉语义、焦点、键盘及深链，真实浏览器覆盖；P2-04 分类播放器错误。
- P2-05：仅按需小粒度抽组件、样式隔离；先保证行为测试，再重构。不要全盘推翻。
- 依 TOP 1–3 做轻量产品迭代，先比较操作步数、状态、可发现性与安全约束。若必须做影响产品定位、长期兼容性、授权范围、真实费用的决定，提交选项让用户决策。

### 阶段 3：独立证据验收与候选 PR
- Python 完整测试、Vitest 完整测试、TypeScript strict、production build、Ruff、git diff --check；使用仓库真实支持命令，避免假定不存在的脚本。
- 真实浏览器（至少桌面 1440×900 与窄屏 390×844、深浅主题）执行：首次导入、内容去重/筛选、媒体 play/seek/error、抽屉 Tab/Shift+Tab/Escape/深链、授权返回/取消/重试、问答候选与拒答、快照和导出。采用合成或公开合法测试数据；不招募真实用户。
- 逐项输出 PASS / FAIL / BLOCKED / NOT_TESTED；注明命令、环境、退出码、时间、准确代码 SHA、真实截图与日志位置。测试桩仅能证明其契约；禁止将跳过、Mock 或未测计入真实端到端通过。
- 输出候选分支与 PR 建议（允许创建草稿 PR 需遵循当前授权；不得自动合入）。保留 main、任务分支和用户工作区。
- 完成后给用户一次可读摘要与独立复审入口。

~~~mermaid
flowchart TD
  M["最新 main：101 个独有提交（审查时）"] --> I["独立集成分支"]
  T["任务分支：116 个独有提交（审查时）"] --> I
  I --> C["审查冲突 / 迁移 / API / 安全契约"]
  C --> S["P1 安全与证据收口"]
  S --> U["P1 UX / 必要 P2 / 回归"]
  U --> V["完整真实验证与证据归档"]
  V -->|FAIL / BLOCKED| S
  V -->|PASS| Q["独立复审 + 用户合入决策"]
~~~

### 运行约束与 SSE EOF 断点恢复
- 保持 Local-First、默认离线、本机原始资料与凭据不外传。真实 Cookie 提取、真实付费 API、实际外部用户测试、删除用户数据、扩大权限、变更产品方向均不在授权内；必须用户明确同意。不得以测试名义访问真实凭据。
- 采用小批次可回滚提交，每批一个明确目标，先测试后提交；保持工作树清晰，不把临时日志/凭据/真实媒体误入 git。
- 每批更新执行 checkpoint（分支、HEAD、git status、已完成 ID、复现结果、测试命令与结果、未完成 ID、下一步与阻塞）；参考现有 EXECUTION_CHECKPOINT.md，但用独立整改记录避免覆盖历史。
- SSE EOF / 网络断流 / 工具中断后，恢复前先核对 HEAD、git status、remote、checkpoint、最后成功测试与未提交差异；从第一个未完成的小批恢复，不重复已完成工作、不盲目重跑网络副作用。有限次重试，无法恢复则记录 BLOCKED。
- 每阶段结束汇报；若跨日运行，每日输出短报告：当前分支/SHA、P1/P2 状态、测试 PASS/FAIL/BLOCKED、风险、下一步、需用户决策项。不能宣称未配置的后台任务已经在运行。

## 8. 最终验收矩阵（AGY 填实际证据）

| Gate | 必须满足 | 初始独立状态 |
|---|---|---|
| M1 集成 | 最新 main + 任务分支独立集成，冲突/迁移/安全契约审查 | NOT_TESTED |
| S1 媒体 | P1-01/02/06、P2-01，合法 200/206/HEAD、416、超限、symlink、Host、故障测试 | NOT_TESTED |
| S2 授权 | P1-04、P2-02，原子频控、最小凭据、假凭据泄漏扫描、DNS/重定向边界 | NOT_TESTED |
| S3 Grounding | P1-03，合法编号错误事实不得认定为已核实；热缓存和历史状态 | NOT_TESTED |
| U1 Reader | P1-05，真实浏览器焦点、ARIA、双主题 390px、深链、play/seek/error | NOT_TESTED |
| U2 核心体验 | 首页、去重、授权回流、问答范围、Vault 导出与恢复，保留用户任务 | NOT_TESTED |
| E1 工程 | 完整 Python/Vitest/TS/Build/Ruff/diff；兼容性、数据安全 | NOT_TESTED |
| E2 证据 | 更新后的报告与实机截图、原始日志、准确代码 SHA；真实外部能力未测标注 | NOT_TESTED |
| R1 合入 | P1 全部解决或有实据反证；P2 状态透明；独立复审、用户批准 | HOLD |

验收报告建议归档于本目录，附真实截图索引和相对路径。截图至少涵盖：稀疏首页、内容去重、Reader 主视区、抽屉开/关（焦点）、390px 深浅主题、受阻授权恢复、问答拒答/真实引用、Vault 区、播放器错误与播放进度。对真实截图脱敏；严禁将本文件 Mermaid 代替实机验证。

**最终纪律：未通过的 gate 不得宣布商业级就绪。禁止擅自合并 main。**
