# 02｜真实市场研究与证据台账（Phase 2 Market Research）

- **研究日期**：2026-11-26（Asia/Shanghai）
- **研究准则**：所有市场事实、价格区间、开源规模与社区痛点均来自 2025–2026 年可公开访问的一手页面、GitHub API、Reddit、Hacker News、V2EX/中文社区与学术/行业公开报道；凡无法从公开渠道直接证实的用户规模、转化率或收入均明确标注为 `[假设 / 待验证]`。

---

## 一、四大核心市场趋势（有真实公开证据支撑）

### 趋势 1：单点 AI 摘要插件陷入“订阅疲劳”，付费意愿向“工作流闭环 + BYOK 买断/可控成本”迁移
- 大量只做 YouTube 一键摘要的浏览器扩展（如 Eightify 年付约 $3.95–$4.95/月、月付 $8–$10/月；Glasp Pro 2026 年 5 月涨至 $15/月）在 Reddit 上遭遇强烈的 **“Death by a Thousand Subscriptions”** 抵触。用户不愿为单一能力再多付一份月费。
- 与此同时，支持 **BYOK（自带 API Key）或接入本机 Ollama** 的桌面端生产力工具展现出清晰的独立开发者付费验证：TypingMind（$39–$99+ 一次买断）与 BoltAI（$79–$399 永久授权）证明，开发者与重度知识工作者愿意为**“消除月费焦虑 + 掌控自己数据与模型路由的干净工作台”**支付 $39–$100 的软件费用。

### 趋势 2：云端巨头（NotebookLM）的三大结构性短板正在催生“本地优先替代品”需求
- Google NotebookLM（现已并入 Gemini Notebook 定价体系：免费 5 小时动态算力池 + 周上限，Plus $4.99/月 2x、Pro $19.99/月 4x、Ultra $99.99–$199.99/月）虽在播客化总览与源内引用上口碑极好，但 Reddit (`r/notebooklm`) 与 HN 社区暴露出五项结构性不满：
  1. **动态算力黑盒限流**：取消固定次数的按 5 小时滚动算力池触发高频研究中断；
  2. **无自动化频道/主题持续追踪**：仍依赖人工逐个粘贴链接；
  3. **源视频失效即被清理（Source Rot）**：YouTube 源视频转私密或删除后约 30 天会被移出 Notebook，破坏长期研究连续性；
  4. **纯云端与跨笔记本孤岛**：无法同时跨所有笔记本检索，且无法直接生成原生 Obsidian Markdown 双链目录；
  5. **仅看字幕不看画面**：对技术视频中的 PPT 架构图、代码和图表存在视觉盲区。
- 开源社区对这一痛点的回应极其剧烈：`MODSetter/SurfSense`（16,960 Stars，Apache-2.0）、`Mintplex-Labs/anything-llm`（68,661 Stars，MIT）、`khoj-ai/khoj`（38,262 Stars，AGPL-3.0）、`danielmiessler/Fabric`（44,773 Stars，MIT）及 `karakeep-app/karakeep`（30,866 Stars，AGPL-3.0）持续高增长，印证用户迫切需要可本地部署或混合控制的知识引擎。

### 趋势 3：2025–2026 年“忠实废话（Faithful Slop）”引发信任危机，“防御性核验（Defensive Verification）”成为刚需
- 2025–2026 年多家学术机构、法律界（如美国第十巡回上诉法院新规）与医疗期刊审查发现 AI 幻觉引用激增，Perplexity 等搜索式 AI 也被多次指出存在“把零散片段缝合成看似严谨的虚假链接/误读数字”的问题。
- 行业话语已从“AI 能不能写得好听”转向**“防御性核验”**：用户要求**原文存在性核验 + 原话内容核验 + 推理与事实严格分层**，以及一秒点击跳转原片精确时间戳（`?t=`）或文档行号的能力——这恰恰是 **Intelligence 当前最稀缺的工程资产**。

### 趋势 4：跨语言技术学习者（YouTube + B站 + Obsidian）存在极强的“去噪监听 + 知识资产化”需求
- 面向中英双语开发者与研究者，B站 + YouTube + 本地文档混合消费是常态，但现有生态高度割裂：BibiGPT 在国内凭“B站+YouTube+思维导图+Obsidian URL Scheme 导出”走红，但采用分钟数包月/按量充值模式（Plus 约 $19.8/月，Pro 约 $34.8/月，免费试用约 120 分钟很快耗尽）；另一方面，YouTube 创作者泛滥的 Shorts 与水视频令追踪 20+ 频道的重度用户遭遇严重通知疲劳，呼唤**先自动折叠噪音与按兴趣过滤、再只精读高信噪比长内容并自动落盘 Obsidian** 的完整管线。
- 此外，**Mem.ai 在 2026 年底宣布关闭（2026 年 12 月只读、2027 年 1 月停服）**在 Reddit (`r/PKMS`) 引发强烈警示效应：把个人多年笔记与知识关系锁定在闭源云端笔记 SaaS 中极度危险，“**本地 SQLite + 一键开放 Markdown/Obsidian 迁移权**”不再是极客洁癖，而是现实资产安全底线。

---

## 二、结构化市场证据台账（2026-11-26 实测抓取）

| ID | 核心结论 / 市场信号 | 规范来源 URL | 获取日期 | 证据摘要 | 可信度 |
|---|---|---|---|---|---|
| **M-01** | NotebookLM 动态 5 小时算力池、源上限及删除视频 30 天失效机制 | https://www.reddit.com/r/notebooklm/ / Google AI Plans (`notebooklm.google`) | 2026-11-26 | 免费 100 笔记本 / 单本 50 源，按 5 小时+周 Ceiling 动态扣减算力；Plus $4.99/mo (2x)、Pro $19.99/mo (4x)、Ultra $99.99–$199.99/mo；YouTube 仅读字幕且删/私密视频约 30 天清理；跨笔记本不能联动问答。 | **High** |
| **M-02** | Mem.ai 2026 年底停止服务引发云端 PKM 信任危机 | https://www.reddit.com/r/PKMS/ | 2026-11-26 | Mem 在 2.0 多次大改版并定价 $12/月后，于 2026 年底公告停止服务（12 月只读、2027 年 1 月关闭），引发用户大规模迁往 Obsidian/本地 Markdown。 | **Medium-High** |
| **M-03** | Readwise Reader 捆绑 $120/年定价引发订阅疲劳与拆包呼声 | https://readwise.io/pricing / https://www.reddit.com/r/ObsidianMD/ | 2026-11-26 | Full 套餐约 $12.99/月或 $119.88/年（捆绑经典 Readwise）；用户普遍赞誉其排版与 Obsidian 同步，但持续抱怨缺乏更低价的纯 Reader 档及 Ghostreader 摘要扁平化。 | **High** |
| **M-04** | Recall (`recall.it`，原 `getrecall.ai`) 定价与导出/多语言/扣费口碑 | https://www.recall.it/ / https://www.reddit.com/r/ProductivityApps/ | 2026-11-26 | 原 `getrecall.ai` 已重定向至 `recall.it`。免费版限 10 次 AI 摘要/月，Plus ~$10–12/月，Max ~$38–48/月；支持知识图谱+MCP+FSRS复习，但社区抱怨“unlimited”宣传落差、抓取失效与导出不完整。 | **High** |
| **M-05** | BibiGPT 跨 B站+YouTube 市场验证及分钟消耗瓶颈 | https://bibigpt.cn/ / https://bibigpt.co/ | 2026-11-26 | 支持 20+ 平台（YouTube/B站/播客/本地文件）、导图、时间戳与 Obsidian URL Scheme/MCP 同步；免费约 120 分钟快速耗尽，Plus ~$19.8/月（年付折合 ~$142.56/年）、Pro ~$34.8/月，印证双语视频+Obsidian 有高付费意愿，但纯按分钟云端计费存在成本上限焦虑。 | **High** |
| **M-06** | 开源本地 NotebookLM / Second Brain 项目高速增长 | https://github.com/MODSetter/SurfSense / https://github.com/Mintplex-Labs/anything-llm / https://github.com/danielmiessler/Fabric / https://github.com/karakeep-app/karakeep / https://github.com/khoj-ai/khoj | 2026-11-26 | GitHub API 实测：`anything-llm` 68,661 stars (MIT)、`Fabric` 44,773 stars (MIT)、`khoj` 38,262 stars (AGPL-3.0)、`karakeep` 30,866 stars (AGPL-3.0)、`SurfSense` 16,960 stars (Apache-2.0)、`obsidian-local-rest-api` 3,202 stars (MIT)，2026 年 11 月仍高频提交。 | **High** |
| **M-07** | 单点扩展（Eightify/Glasp/Snipd）遭遇聚合替代与订阅疲劳 | https://www.snipd.com/ / https://glasp.co/ / https://eightify.app/ / https://www.reddit.com/r/ObsidianMD/ | 2026-11-26 | Eightify (~$3.95–$4.95/月年付)、Glasp Pro ($15/月，2026.05 上调)、Snipd (~$6.99/月年付或 $11.99/月) 均面临“为单个场景多付一份月费是否值得”的质疑；其中 Snipd 靠通勤耳机快捷剪藏+Obsidian 同步留住泛播客高黏性用户。 | **High** |
| **M-08** | 独立桌面端 BYOK 工具一次性买断 / 分层授权付费意愿 | https://boltai.com/ / https://www.typingmind.com/ / https://obsidian.md/pricing | 2026-11-26 | BoltAI ($79–$399 一次授权)、TypingMind ($39–$99+ 买断)、Obsidian Sync ($4–$8/月) 及商用授权 ($50/年) 证实：用户极度反感“对通用模型加价抽水”，但愿意为干净的本地原生外壳、工作流效率与安全同步付费。 | **High** |
| **M-09** | Heptabase 的“追逐 AI 积分焦虑”前车之鉴 | https://heptabase.com/pricing / https://www.reddit.com/r/heptabase/ | 2026-11-26 | Pro $8.99/月（年付），AI Premium 约 $17.99/月。重度科研/PhD 用户抱怨产品过度追逐消耗 AI Credits 的 Agent 功能，反而忽视文献引用、白板性能和可靠基础体验。 | **High** |
| **M-10** | “忠实废话 (Faithful Slop)”与防御性核验需求 | https://news.ycombinator.com/ / Lancet / IEEE / 法律合规讨论 | 2026-11-26 | 学术与专业界对 AI 捏造参考文献和误读数字高度警惕，催生“存在性+内容真实性+上下文一致性”三步核验流程；无直接原文/时间戳锚点的总结已无法进入严肃研究工作流。 | **Medium-High** |
| **M-11** | YouTube 频道追踪核心痛点：通知轰炸 + 碎片检索盲区 | https://www.reddit.com/r/PKMS/ / https://news.ycombinator.com/ | 2026-11-26 | 用户追踪 20+ 频道后，RSS 只推全量通知（包含大量 Shorts 与水视频），且收藏夹无法搜索“半年前视频第 18 分钟讲过的方法论”，迫切需要“兴趣过滤 + 全库跨视频语义/证据检索 + 自动进 Obsidian”。 | **High** |

---

## 三、明确标注为 `[假设 / 待验证]` 的信息

- **[假设 / 待验证 H-01]**：Intelligence 目标用户群中，同时拥有 Apple Silicon Mac + Obsidian 且对“零幻觉引用 + 自动监控过滤”有强付费意愿的真实转化率（如免费本地版向 Pro 自动化/云协同/买断扩展包的转化比例）。目前尚无真实上线漏斗数据。
- **[假设 / 待验证 H-02]**：单用户每月在“本机 Ollama 过滤/初筛 + 按需 BYOK 深度提炼”混合架构下的精确外部 API 边际成本分布（需结合实测 token 消耗建模并在 09 号文档中明确标为模型测算）。
- **[假设 / 待验证 H-03]**：国内独立开发者/AI 研究者在 YouTube 代理受限环境与 B站直连混用下，对单机桌面封装版 vs CLI+Web 工作台的接受度差异。
