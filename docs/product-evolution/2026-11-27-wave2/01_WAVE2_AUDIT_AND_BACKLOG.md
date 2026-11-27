# 01｜Wave 2 基线实机审计与动态优先级池（Post-Wave-1 Live Audit & Backlog）

- **审计时间**：2026-11-27 00:25–00:32 CST（Asia/Shanghai）
- **基线版本**：Stacked cleanly on Wave 1 (`088554c45f9d8d05818f415871fd124655280969`, PR #52 — 14/14 远端 CI 绿灯)
- **Wave 2 分支**：`antigravity/autonomous-product-evolution-wave2-20261127`
- **审计环境**：
  - 全新空状态本地工作区：`http://127.0.0.1:8798`
  - Curated Demo 工作区：`http://127.0.0.1:8799`（构建包 `assets/index-BaU6AWoY.js`）
  - 实机运行时健康：`0` console errors、`0` pageerrors、`0` HTTP >=400 请求

---

## 一、实机量测与关键界面痛点发现（直接证据）

1. **全新空工作区（`8798`）仍存在首分钟冷启动摩擦**：
   - 见 [Empty Home](./screenshots/baseline/step_9_shot_1_01_w2_empty_home.png) 与 [Empty Content](./screenshots/baseline/step_9_shot_3_03_w2_empty_content.png)：Wave 1 补全了 3 步快速开始说明和「重新查看新手引导」入口，但若用户手头暂无公开链接或文件，仍需先退出或自行寻找素材才能首次看见真实阅读器与证据溯源工作流。
   - 见 [Empty Following](./screenshots/baseline/step_9_shot_2_02_w2_empty_following.png)：空关注页在 `1440x900` 视口中存在两枚样式完全一致的绿色主按钮（右上角 `x=1310, y=159.9` 与空卡片内 `x=325, y=266.9`），主次视觉层级分散（需保留双按钮以维护既有可访问性与测试契约，但应将顶部按钮降级为次级按钮）。
2. **`#Content` 在 `390x844` 移动端首屏被 6 行筛选器挤占（已量测确认）**：
   - 见 [Mobile Content 390px](./screenshots/baseline/step_11_shot_2_05_w2_demo_content_mobile_390.png)：桌面端 `1440x900` 首行内容位于 `y=228.4px`（筛选栏高 `87.5px`），但在 `390x844` 手机端，`.library-filter-bar` 堆叠展开达 **`304.5px`**，将第一条内容卡片（`demo-architecture-notes.md`）推至 **`y=578.59px`**，占满三分之二首屏。
3. **阅读器媒体舞台空态与证据抽屉单条引文复用摩擦**：
   - 见 [Reader Media Dark](./screenshots/baseline/step_13_shot_1_06_w2_reader_media_dark.png) 与 [Reader Media Light](./screenshots/baseline/step_13_shot_2_07_w2_reader_media_light.png)：当无本地关键帧缩略图时，`.reader-media-poster` (`340x191.25px`) 仅展示平台图标、时长与频道名，缺少来源原文就绪状态、证据条数提示及「直达原话证据」快捷入口。
   - 见 [Reader Evidence Drawer](./screenshots/baseline/step_16_shot_1_08_w2_reader_evidence_drawer.png)：抽屉可准确按 `Esc` 关闭，但每条原话证据（共 9 条）底部仅支持跳转原片/查看技术标识，缺乏一键复制标准出处格式（原话 + 标题 + 时间戳/段落位置）的操作。
4. **`#Topics` 跨来源观点对照与 `#Research` 深度追问未打通直达桥**：
   - 见 [Topics Perspectives](./screenshots/baseline/step_19_shot_1_09_w2_topic_perspectives.png) 与 [Research Active](./screenshots/baseline/step_21_shot_1_11_w2_research_active.png)：`#Topics` 已有「跨来源观点对照」卡片，`#Research` 已支持多视频指定对比，但从专题卡片无法一键带入这些对比视频进入 `#Research` 进行结构化共识/分歧提问；同时在得到一次有据回答后，虽然有「同范围继续追问」按钮，但缺少高信噪比预设深挖模板，用户仍面对空白输入框（需坚持只预填不自动提交，避免任何静默云端消费）。
5. **`#Intelligence` 角色定位解释、键盘效率发现与设置页成本透明度**：
   - 见 [Intelligence List](./screenshots/baseline/step_19_shot_2_10_w2_intelligence_list.png)：虽在 `1440px` 与 `390px` 下零横向溢出，但用户首次进入时需一眼理解「洞察（长期可复用判断库） vs 内容（待读/分诊池）」的心智分工；同时系统已有 `/`、`J/K`、`S/E/U`、`⌘K` 等效率快捷键却缺少全局 `?` 快捷键指南与 `⌘K` 高优未读分诊直达；[Settings Engine](./screenshots/baseline/step_23_shot_2_13_w2_settings_engine.png) 缺少一眼看懂「本机 Ollama ￥0 零成本 vs 云端 BYOK 预算隔离」的只读成本与适用场景对比指南。

---

## 二、Wave 2 动态优先级需求池（按评分公式重排）

评分公式：$\text{Score} = 0.20\times\text{Pain} + 0.20\times\text{Value} + 0.15\times\text{Evidence} + 0.15\times\text{Diff} + 0.10\times\text{Retention} + 0.10\times\text{Monetization} + 0.10\times\text{Feasibility}$

| 优先级 | Wave 2 ID | 对应迭代 | 需求名称 | 目标人群 | 总分 | 证据可信度 | 风险与契约守则 | 独立可回退设计 |
|---|---|---|---|---|---:|---|---|---|
| **1** | **EVO-W2-01** | **Iter 6** | **新手零门槛闭环：内置安全示例笔记一键体验 + 空关注页层级降噪** | 全部新用户（Day 1） | **8.90** | **High** (`01`/`02`/`03` 实测) | 无网络、走真实 `POST /api/v1/local/imports` 校验；保留双 `Add Source` 按钮契约 | 独立 commit |
| **2** | **EVO-W2-02** | **Iter 7** | **专题→研究「对比共识与分歧」直达桥 + 追问模板** | 研究者 / 分析师 | **8.75** | **High** (`09`/`11` 实测) | 仅预填可编辑问题框，绝不自动发起花费/模型请求 | 独立 commit |
| **3** | **EVO-W2-03** | **Iter 8** | **`#Content` 两级分诊工具栏 + `390x844` 移动端首屏上提** | 全人群（桌面+手机巡检） | **8.55** | **High** (`05` 量测 `y=578.59px`) | Desktop 与 jsdom 保持全部筛选可交互，仅 `<768px` 折叠次级筛选与单行滚动胶囊 | 独立 commit |
| **4** | **EVO-W2-04** | **Iter 9** | **阅读器社论式媒体舞台卡片 + 原话引用一键复制 + 移动端关键帧精修** | 研究者 / Obsidian 用户 | **8.35** | **High** (`06`/`07`/`08` 实测) | 严守逐字原话（不改写原文）、不破坏 `ReaderReferenceDrawer` focus-trap 与 `inert` | 独立 commit |
| **5** | **EVO-W2-05** | **Iter 10** | **`#Intelligence` 判断库心智清晰化 + `?` 快捷键指南 + `⌘K` 高优分诊快捷动作** | 高频键盘用户 / 研究者 | **8.10** | **High** (`10`/`12` 实测) | 严格保持 `<nav>` 仅 6 个主导航按钮；`?` 在输入框聚焦时自动屏蔽 | 独立 commit |
| **6** | **EVO-W2-06** | **Iter 11** | **`#Settings` 本机 vs 云端 BYOK 只读成本透明度说明 + 全端全视图精细化扫尾** | 自托管用户 / PM | **7.95** | **High** (`13` 实测) | 严格只读估算说明，绝不触发付费接口或弱化预算/凭据守卫 | 独立 commit |

> 注：`EVO-06`（直接向宿主真实 Obsidian Vault 写文件）在 Wave 2 仍保持 **DEFER**，需待项目所有者进行 L3 安全边界批准后再单独立项。
