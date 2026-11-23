# 30 天产品与运营迭代路线图（Internal Iteration Roadmap）

- **规划周期**：2026-11-23 至 2026-12-22
- **总体阶段方针**：当前处于**内部自主迭代与产品完善阶段**（未获创始人明确进入下一阶段指令前，严禁发起任何面向真实外部用户的邀测、招募或公开推广实验）。全部研发、UX、QA 与资产打磨均聚焦“把核验主航道磨成零死角高可靠单机作品”。

---

## Week 1（11/23 – 11/29）：全景接管 · 实机清障 · 操作系统建制（已完成核心启动）
- [x] **Day 1 – Stage A/B 全面接管与研究**：完成 10 维产品技术基线审计、双端口 Chromium（Demo + 新建 `youtube-intel start` 空库）AI 模拟巡检、以及 NotebookLM / BibiGPT / Readwise Reader / Open Notebook / Obsidian BYOK 市场与定价交叉研究。
- [x] **Iteration #1 (`09f98d4`) & `EXP-002` 本机模型实测**：补齐全导出链路安全 HTTPS `?t=` 原片深链与 `ev:` 出处指纹；用真实本机 `ollama/qwen3.5:9b` 跑通 3/3 跨源问答 + 2/2 诱骗拒答。
- [x] **Iteration #2 (`a820152`) 零配置冷启动**：交付 `uv run youtube-intel start`、`--check-only` 环境清单、`serve-api` `vault_root` 友善提示及新版 `README.md` 5 分钟极速指引，CI `#45137542384` 双端全绿。
- [x] **Iteration #3 (`fee43f4`) & `FD-005` 主线 CI 合流 (`main@f23954f`)**：
  - 根治 Demo 越域对抗问题伪引用、`youtube-intel start` macOS 浏览器本地文件上传阻塞、冷启动 Settings 假“待检查”、空库 `#Research` HTTP 409 死路与 `Escape` 关闭缺失；
  - 补全 15 份运营文档与 CPO 日报体系；同步上 `main@f23954f` 达成 GitHub Actions `#45149288840` 双端全绿。
- [x] **Iteration #4 (`BL-006` + `BL-005` · `6760028` on `antigravity/task-user-readiness-20261112`)**：
  - 交付 `FastReadApiApplication` 单快照 `/evidence` 加速（实测冷读 `39.6ms` / 热读 `3.8–5.8ms`）+ 前端 SWR 无闪烁保留 + `.reader-action-bar` 两层重构与移动端快捷键徽章收敛；
  - 扩充多源反幻觉与冲突归因 Eval 集至 32 例，并加固 Demo 复合域外问题诚实拒答。
- [x] **Iteration #5 (`BL-007` · `2be958f` on `antigravity/task-user-readiness-20261112`)**：
  - 首轮三步引导升级可点击步骤导航条、祖母绿品牌进度条与 3 来源结构化卡片，空态首页补齐格式提示；
  - 补全 `Organized`/`Review Content`/`Position unavailable`/`Investigations` 等缺失中文词条并清理 `UNKNOWN`/冗长提示，`54/54` (`1244/1244`) Vitest 全绿并通过 Obsidian Dark 桌面 + Warm Paper Light 移动实机核验。
- [x] **Iteration #6 (`BL-008` 提前交付完成 · `antigravity/task-user-readiness-20261112`)**：
  - 突破 500 条视频硬截断：向后兼容 `/api/v1/videos?limit=&offset=` 分页与 8 处全库分块读取（600 条实测跨库问答 `0.23s`、3 页分页 `48–98ms`）；
  - 交付 SQLite 原生 `.backup()` 零密钥热快照 `hub-snapshot.sqlite3`（`5.5ms` / `0o600` / `integrity_ok`），冷启动路径提速至 `68.56ms`/`21.90ms`，11 组 CI `pytest` `143/143` + 备份 `27/27` 全绿；复核 `#Settings` 已默认折叠收起保持零 UI 扰动。

## Week 2（11/30 – 12/06）：长视频多轮边界压测 & Obsidian 实机目录走查（L1/L2 内部打磨）
- [ ] **长视频多轮边界与大库恢复抽检**：在隔离环境中抽检真实多小时本地课程与混合 Markdown 长文本在 600+ 条库存下的端到端导出与备份恢复稳定度。

## Week 3（12/07 – 12/13）：可恢复性、离线打包边界与商业前提自查
- [ ] **离线打包边界与极简脚本预设评估**：梳理真实安装报错与单机运行前置检查体验（正式发行评估 `BL-009` 仍需等未来真人首测放行后校准）。
- [ ] **Obsidian Vault 导出目录结构实机美化**：在隔离 `.var/workspace/vault` 验证导出 `.zip` 与文件夹解压后在真实 Markdown 结构中的 `[[wikilinks]]`、Frontmatter 与 `?t=` 点击流畅度（不触碰创始人真实个人 Obsidian Vault）。
- [ ] **梳理阶段退出检查单（Ready-for-Human-Testing Gate）**：逐项核对 `P0/P1` 遗留缺陷 = `0`、安装成功一键检查完善、支持材料（FAQ/5分钟教程）完备，整理呈报创始人审阅。

## Week 4（12/14 – 12/22）：内部全量审计收口 & 等待创始人阶段放行裁决
- [ ] **全仓库二次全面审计与代码瘦身**：剔除未复用临时组件，确保安全扫描零新增、CI 套件继续保持零 skip 100% 全绿。
- [ ] **提请创始人最终裁决（L3）**：
  - 由创始人决定是否批准结束“内部自主迭代阶段”、按何种节奏合并开发提交至 `main`，以及是否授权启动小范围首批外部用户试跑。在获得明确口头/书面放行前，绝不越线执行任何真人测试动作。
