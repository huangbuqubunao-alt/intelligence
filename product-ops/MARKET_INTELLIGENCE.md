# 持续市场与行业情报库（Market Intelligence）

- **最近全面更新日期**：2026-11-23（Stage B 深度交叉调研更新）
- **调研边界说明**：所有外部判断均明确标注信息来源、获取日期、适用范围与可信度等级，严格区分 **已证实的市场公开事实 / 合理行业推断 / 待本产品自身验证假设**。

---

## 一、行业变化与商业定价基准

### 1. Google NotebookLM 分级与社区核心痛点（外部直接标杆）
- **已证实公开事实**（获取日期：2026-11-23；来源：`search_web` 交叉汇总 `r/notebooklm`、`r/ObsidianMD`、Hacker News 及公开定价帮助资料）：
  - Google NotebookLM 采用分级 AI 体系（Free 基础免费；Plus 约 **\$4.99/月**；Pro 约 **\$19.99/月**；Ultra 约 **\$99.99–\$199.99/月**），由固定日次转为滚动算力配额。
  - **YouTube 仅支持公开带字幕视频**，无原生 B 站 `BV` 适配；作为封闭云端工作台，导出到 Obsidian 等本地 `.md` 库高度依赖社区脚本（如 `nb2ob` 等工具）手动桥接，本地修改源文档后无法原地增量更新。
  - **社区痛点讨论（定性证据，适用高密度科研/重度文档用户）**：在 Reddit `r/notebooklm` 及 Hacker News 讨论中，用户反馈处理超长复杂 PDF/混排材料时仍会出现**数字张冠李戴、跨大文件上下文丢失及混入外部通用训练知识**的问题；进阶用户被迫手工切分 15–20 页 Markdown 预处理后才上传。
- **可信度**：**中高**（多社区长期讨论交叉印证，但不代表所有轻量用户都有相同敏感度）。
- **对 Intelligence 的启发**：本地 `Markdown` 原生接入、切片锁哈希 (`TEXT_RANGE`) 以及严格的 `REFUSED_INSUFFICIENT_EVIDENCE` 机制正好打在大厂云产品的结构短板上，但大厂免费与零部署仍是巨大体验压力源。

### 2. 中文长视频工具生态：按分钟计费压力与工作流割裂
- **已证实公开事实**（获取日期：2026-11-23；来源：`search_web` 检索 `bibigpt.co`、`exploreai.directory`、`textivore.com` 等 2025–2026 公开定价与评测）：
  - **BibiGPT（面向 B 站/YouTube/播客的中文头部 SaaS）**：依赖多模态大模型与云端 ASR 导致按量/月费刚性；Plus 约 **\$19.80/月**（年付折约 \$142.56/年，限本地文件月时长额度），Pro 约 **\$34.80/月**（年付约 \$250.56/年，解锁无限本地视频及高阶同步）；新用户体验额度有限，且社区评测指出其主要解决单条视频速览，若只导出不精炼易造成“收藏了但没真正内化（数字囤积）”陷阱，同时受平台风控变化影响明显。
  - **Readwise Reader（高价值稍后阅读 & Obsidian 同步标杆）**：无永久免费版（仅 30 天试用）；Reader 独立版约 **\$7.99/月（年付 \$95.88/年）** 或 **\$8.99–\$12.99/月（按月）**；Full Readwise（含间隔重复回顾）约 **\$9.99/月**，学术群体享 50% 折扣。其强项是极其顺滑的高亮同步 Obsidian 体验，但主要服务英文阅读生态、纯订阅收费、数据留云端、且完全不适配 B 站和本地零费用模型转写。
- **可信度**：**中高**（官方定价页可核验；痛点归纳来自公开评测文章及用户分享，存在中文重度群体偏斜）。

### 3. 本地优先 / Open-Core PKM 与 BYOK 商业模式基准
- **已证实公开事实**（获取日期：2026-11-23；来源：`gh api` + `search_web` 检索 Obsidian 插件生态与 Open-Core 开源产品公开定价）：
  - **GitHub 开源竞品热度（`gh api` 一手实测）**：
    - `Mintplex-Labs/anything-llm`：**68,521★**（MIT）
    - `danielmiessler/Fabric`：**44,745★**（MIT）
    - `lfnovo/open-notebook`：**42,146★**（MIT，多源研究+多说话人 AI 播客，自托管 Docker）
    - `khoj-ai/khoj`：**38,212★**（AGPL-3.0）
    - `MODSetter/SurfSense`：**16,929★**（Apache-2.0，连接 Slack/Notion/GitHub/YT/Web）
    - `logancyang/obsidian-copilot`：**8,033★**（AGPL-3.0）
    - `JefferyHcool/BiliNote`：**7,812★**（MIT，专注 B 站/视频转 Markdown 笔记）
  - **开源与 PKM 插件主流定价区间（已证实行业基准）**：
    - **纯开源核心 + BYOK/Ollama**：**\$0**（用户自备 API Key 或跑免费本地 Ollama，开发者免于承担 Token 垫资与信用卡合规负担）。
    - **Obsidian 插件 / 本地工具 Pro 增值档**（如 `Obsidian Copilot` / `Smart Connections` / `SystemSculpt` 模式）：**\$9–\$15/月**（或约 **\$90–\$140/年**，少数提供 **\$300+** 终身支持档），收费卖点主要是托管加速检索后端、免折腾模型代理与高级工作流模板，而非锁死用户本地文件。
    - **Open-Core 团队私有/云工作空间**（如 `AppFlowy` / `AFFiNE`）：**\$10–\$15 / 席位 / 月**（按年计费），收费锚点为团队共享图谱、管理员权限与合规模版。
    - **社区极度反感点**：Reddit 与 Hacker News 对“只做一层薄薄的 RAG 套壳界面就收取高额月租”极度警惕与反感；相比之下，“核心开源透明 + 数据全归个人本地 Vault + 只在真省时间的高阶工作流或团队治理上收费”最易获开发者与科研群体正面口碑。
- **可信度**：**高**（开源 Star 数与主流竞品价格表有直接事实依据）。

---

## 二、情报来源与可信度审计表

| 情报主题 | 信息来源 | 获取日期 | 适用范围 | 可信度 | 是否验证过本产品用户 |
|---|---|---|---|---|---|
| 开源生态 `AnythingLLM`/`Open Notebook`/`SurfSense`/`BiliNote`/`obsidian-copilot` 活跃度与协议 | `gh api` REST 一手抓取 | 2026-11-23 | GitHub 全球开发者开源选型趋势 | **高** | 否（外部生态对照） |
| Google NotebookLM 分级定价、5h 算力窗及 Obsidian/幻觉抱怨 | `search_web`（官方帮助/定价报道 + Reddit `r/notebooklm`） | 2026-11-23 | 重度英文科研/文档用户 | **中高** | 否 |
| BibiGPT Plus/Pro（\$19.8 / \$34.8/月）与 Readwise Reader（\$7.99–\$9.99/月）定价及用户痛点 | `search_web`（`bibigpt.co` / `readwise.io` 公开信息及社区评测） | 2026-11-23 | 中英视频学习 & Read-later 用户 | **中高** | 否 |
| Obsidian 插件与 Open-Core PKM 定价基准（BYOK \$0 / Pro \$9–15/月 / Team \$10–15/席位） | `search_web`（Obsidian 插件生态及 `opensourcealternatives.to` 汇总） | 2026-11-23 | Local-first PKM 商业模式参照 | **中** | **待未来真实用户验证** |
