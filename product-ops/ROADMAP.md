# 30 天产品与运营迭代路线图（Internal Iteration Roadmap）

- **规划周期**：2026-11-23 至 2026-12-22
- **总体阶段方针**：当前处于**内部自主迭代与产品完善阶段**（未获创始人明确进入下一阶段指令前，严禁发起任何面向真实外部用户的邀测、招募或公开推广实验）。全部研发、UX、QA 与资产打磨均聚焦“把核验主航道磨成零死角高可靠单机作品”。

---

## Week 1（11/23 – 11/29）：全景接管 · 实机清障 · 操作系统建制（已完成核心启动）
- [x] **Day 1 – Stage A/B 全面接管与研究**：完成 10 维产品技术基线审计、双端口 Chromium（Demo + 新建 `youtube-intel start` 空库）AI 模拟巡检、以及 NotebookLM / BibiGPT / Readwise Reader / Open Notebook / Obsidian BYOK 市场与定价交叉研究。
- [x] **Iteration #1 (`09f98d4`) & `EXP-002` 本机模型实测**：补齐全导出链路安全 HTTPS `?t=` 原片深链与 `ev:` 出处指纹；用真实本机 `ollama/qwen3.5:9b` 跑通 3/3 跨源问答 + 2/2 诱骗拒答。
- [x] **Iteration #2 (`a820152`) 零配置冷启动**：交付 `uv run youtube-intel start`、`--check-only` 环境清单、`serve-api` `vault_root` 友善提示及新版 `README.md` 5 分钟极速指引，CI `#45137542384` 双端全绿。
- [x] **Iteration #3 (`fee43f4`) & Stage C/E 全系统对齐（今日完成）**：
  - 根治 Demo 越域对抗问题伪引用、`youtube-intel start` macOS 浏览器本地文件上传阻塞、冷启动 Settings 假“待检查”、空库 `#Research` HTTP 409 死路与 `Escape` 关闭缺失；
  - 补全 `BACKLOG.md`、`COMMERCIALIZATION.md`、`OPS_ASSETS.md`、`TEST_LOG.md`，日报脚本升级支持 `--template cpo` 与严格内部边界守护。

## Week 2（11/30 – 12/06）：信息架构精简 · 核心交互手感与性能磨平（L1/L2 内部打磨）
- [ ] **UI Craft 精简化收敛（基于 Stage A/D 走查反馈）**：
  - `BL-007`：精简 `#Content/<id>` 详情页顶部 9 按钮多行换行冗余，收敛次要动作为二级折叠菜单，突出“原文证据核对 + 一键拷贝/导出”；
  - `BL-008`：排查并解决 `#Content/vidDemoAgt1` 展开证据偶发短时停留加载提示的 SWR 预热体验，优化大库检索分页响应；
  - `BL-009`：复查 `Settings` 次级卡片文案与“暖纸浅色 / 黑曜石深色”双主题对比度，践行 craft-floor 极简原则，删掉不必要的说明文字。
- [ ] **内部基准扩充（`$0` 本机运行）**：用 `qwen3.5:9b` 与 `gemma4:12b` 在不同硬件窗口尺寸下测试 1 小时以上长文本切片与多篇 `.md` 混排冲突检测，完善自动化 Eval（目标 >=30 例）。

## Week 3（12/07 – 12/13）：可恢复性、离线打包边界与商业前提自查
- [ ] **大库备份恢复与长视频边界压测**：验证 500 条以内真实规模库下的 backup/restore 全链路一致性与 JSON 导出耗时。
- [ ] **Obsidian Vault 导出目录结构实机美化**：在隔离 `.var/workspace/vault` 验证导出 `.zip` 与文件夹解压后在真实 Markdown 结构中的 `[[wikilinks]]`、Frontmatter 与 `?t=` 点击流畅度（不触碰创始人真实个人 Obsidian Vault）。
- [ ] **梳理阶段退出检查单（Ready-for-Human-Testing Gate）**：逐项核对 `P0/P1` 遗留缺陷 = `0`、安装成功一键检查完善、支持材料（FAQ/5分钟教程）完备，整理呈报创始人审阅。

## Week 4（12/14 – 12/22）：内部全量审计收口 & 等待创始人阶段放行裁决
- [ ] **全仓库二次全面审计与代码瘦身**：剔除未复用临时组件，确保安全扫描零新增、CI 套件继续保持零 skip 100% 全绿。
- [ ] **提请创始人最终裁决（L3）**：
  - 由创始人决定是否批准结束“内部自主迭代阶段”、按何种节奏合并开发提交至 `main`，以及是否授权启动小范围首批外部用户试跑。在获得明确口头/书面放行前，绝不越线执行任何真人测试动作。
