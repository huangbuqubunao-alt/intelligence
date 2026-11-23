# 30 天产品与增长路线图（Roadmap · Day 1 – Day 30）

- **规划周期**：2026-11-23 至 2026-12-22
- **总体策略**：前 15 天只抓 **“可信度证明 + 开源触达 + 前 10 名真人闭环试跑”**，用真实验收数据倒逼后 15 天决定做不做打包与增值功能；坚决不在无真实留存证明前扩写 V2 爬虫。

---

## Week 1（11/23 – 11/29）：主线整合 · 真实模型基准包 · 对外可看状态
- [x] **Day 1（已完成）**：建立 `product-ops/` 全套运营决策基线、市场/竞品矩阵、交付 **可携带深链引用与导出出处（`09f98d4`）** 与每日日报生成器 [generate_daily_ops_report.py](../scripts/generate_daily_ops_report.py)。
- [x] **`EXP-002`（真实本机模型实测基准包，2026-11-23 完成）**：在隔离临时工作区用真实本机 `ollama/qwen3.5:9b` 跑通跨源双语对照（3/3 `GROUNDED`，同时引用 YouTube `&t=85s` + B 站 `?t=115` + Markdown `TEXT_RANGE P2 (47–213)`）及 2/2 诱骗问题诚实拒答（`REFUSED_INSUFFICIENT_EVIDENCE`，总耗时 `227.6s`），并核验 Obsidian Markdown 深链导出零 `00:00` 伪时间戳。
- [x] **`FD-001`（2026-11-23 已完成）**：整合核心加固/迭代及跨平台 CI 修复至 `main@9f65417a6589823096bea5c6ae7d7580a602822a`，推送 `origin/main`，GitHub Actions [`Public Beta CI #45132090574`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45132090574) Python + Frontend 双端全绿通过。
- [x] **补充零配置启动器与首次试用 5 分钟上手清单（`DEC-OPS-005` & `FD-004` · 2026-11-23 已完成并上 `main@a820152`）**：新增 `uv run youtube-intel start`（`--check-only` / `--vault` / `--workspace-root`）、`serve-api` `vault_root` 友好排错提示及新版 `README.md` 5 分钟清单；CI [`#45137542384`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45137542384) 双端全绿。

## Week 2（11/30 – 12/06）：Public Beta 对外亮剑与首批 10 位研究者实测
- [x] **`FD-002`（2026-11-23 仓库已公开）**：GitHub 仓库 `huangbuqubunao-alt/intelligence` 已转为 **`PUBLIC`**（Apache-2.0），并备好面向 **5–10 名深度用户的 `EXP-001` 私域试用邀请文案**，待创始人发出后持续回收首轮激活与留存反馈。
- [ ] **观测冷启动激活漏斗**：记录每位受试者从 Clone 到看到第 1 份跨源问答导出耗时、报错卡点（如 `yt-dlp` / Ollama 模型拉取 / B 站字幕权限 / 端口冲突）。
- [ ] **每周竞品巡检（W49）**：更新 `open-notebook`、`BiliNote`、Google NotebookLM 与 BibiGPT 动态。

## Week 3（12/07 – 12/13）：基于真实摩擦的高胜率修复冲刺
- [ ] **按真实阻碍排 P0/P1 修复（L1/L2 自主推进）**：预期可能集中在冷启动一键自检引导（`doctor --fix` 或清晰的缺失依赖交互提示）、B 站/YouTube 常见失效提示美化，以及一键打开本地 `.md` 到默认 Obsidian 目录的便捷工作流（仅以实测高频痛点为准，不事先臆测）。
- [ ] **产出至少 1 篇由本工具实际产出的高水准对照研究样本文章**：展示“真实一手英文原话如何修正了中文解读中的某个条件误判”，直接回应产品差异化评审需求。

## Week 4（12/14 – 12/22）：第 14 天留存复盘、PMF 判定与商业化实验门槛决策
- [ ] **复盘 `EXP-001` 真实数据**：
  - 核查 **首次成功率**（目标 `>=60%`）与 **Day-7 回访留存**（目标 `>=30%`）。
- [ ] **触发战略裁决 Gate**：
  - **若达标**：进入 **Stage 2（增长与商业化实验）**——制定原生安装包装方案或「Pro 自动化 Obsidian Vault 同步/团队研报包」最小收费假设测试（`EXP-003`），并单独提报 L3 决策。
  - **若未达标（例如冷启动掉队 >60% 或用户反馈回流 NotebookLM）**：依据真实访谈证据向创始人提交「简化架构 / 转型聚焦轻量 CLI·Obsidian 插件 / 或止损」的 L3 决策报告。
