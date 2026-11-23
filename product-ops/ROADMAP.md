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
- [x] **Iteration #6 (`BL-008` · `dbc7e89` on `antigravity/task-user-readiness-20261112`)**：
  - 突破 500 条视频硬截断：向后兼容 `/api/v1/videos?limit=&offset=` 分页与 8 处全库分块读取（600 条实测跨库问答 `0.23s`、3 页分页 `48–98ms`）；
  - 交付 SQLite 原生 `.backup()` 零密钥热快照 `hub-snapshot.sqlite3`（`5.5ms` / `0o600` / `integrity_ok`），冷启动路径提速至 `68.56ms`/`21.90ms`，11 组 CI `pytest` `143/143` + 备份 `27/27` 全绿；复核 `#Settings` 已默认折叠收起保持零 UI 扰动。
- [x] **Iteration #7（`BL-010` 交付完成）& `FD-006` 主线 CI 合流（`main@aec26da`）**：
  - 修复 4 小时课程（`14390s`）& 300KB+ Markdown 全篇均匀边界采样、`<=180B` UTF-8 中文安全标题、Windows 保留文件名防护（`_CON`）、大小写碰撞防覆盖、全量 YAML 转义、CommonMark 空行修复与文本笔记无 `00:00` 假时长；新增 `test_long_media_and_obsidian_vault.py` 接入 `.github/workflows/ci.yml`（`028d10e`）并落地 [`RELEASE_READINESS_GATE.md`](./RELEASE_READINESS_GATE.md)；
  - 按创始人 **`FD-006`** 批复完成 Iteration #4–#7 + CI 接线合流 `main@c15cf06`，GitHub Actions [`Public Beta CI #45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845) 双端全绿（`1244/1244` 前端 + `146/146` 后端）。
- [x] **Iteration #8（`BL-011` 交付完成）& `FD-007` 主线 CI 合流（`main@092951b`）**：
  - 交付按需轻量本地视频关键帧抽取 + 64 位 dHash 去重（3–12 帧、`<=960px` JPEG、`0o700`/`0o600`）+ 原话字幕时间对齐融合分析 MVP；复用 BYOK 安全/预算账本与原生 Ollama `/api/chat` `images`（`409 LOCAL_VISION_MODEL_UNSUPPORTED` 防盲发）、原子暂存与 Sidecar 备份还原；
  - 交付双主题关键帧图卡、讲者/PPT 筛选、Lightbox 键盘导航（`ArrowRight`/`Escape`）、单视频 `visual-pack.zip` 及全库 Vault `obsidian-bundle.zip` `assets/*.jpg` 导出；通过真实 `ollama/gemma3:4b` `$0` 实机与双主题 Chromium E2E，并按创始人 **`FD-007`** 批复线性合并 `main@092951b`，GitHub Actions [`#45201809374`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45201809374) 双端全绿（`55/55` / `1247/1247` 前端 + 13 组 `151/151` 后端）。
- [x] **Iteration #9（`BL-012` 交付完成）& `FD-008` 主线 CI 合流（`main@c54b818`）**：
  - 交付 `⌘K` 「查看专题洞察」与「围绕专题追问」直达动作、`#Topics` 搜索/仅看置顶/三模式排序工具条、Research 多行输入防遮挡与 `5px` 双主题细滚动条；
  - 交付 `youtube-intel start --check-only` 一行式就绪结论（`[ALL READY]`/`[READY WITH WARNINGS]`/`[ACTION NEEDED]`/`[BLOCKED]`）、Ollama 模型溢出计数 `(+N more)` 与 `ffmpeg` 关键帧提示；按创始人 **`FD-008`** 批复线性合并 `main@c54b818`，GitHub Actions [`#45216029723`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45216029723) 双端全绿（`56/56` / `1249/1249` 前端 + 13 组 `152/152` 后端）。

## Week 2–3（11/30 – 12/13）：持续内部巡检与极简安装边界储备（L1/L2 内部打磨）
- [ ] **增量文档/引导清晰度走查与安装报错预设检查**：在不开启新战线前提下复核新用户首次运行 `--check-only` 的错误引导可读性（正式发行打包 `BL-009` 仍待未来真人首测放行后再定）。

## Week 4（12/14 – 12/22）：内部全量审计收口 & 等待创始人阶段放行裁决
- [ ] **全仓库二次全面审计与代码瘦身**：剔除未复用临时组件，确保安全扫描零新增、CI 套件继续保持零 skip 100% 全绿。
- [ ] **提请创始人最终裁决（L3）**：
  - 由创始人决定是否批准结束“内部自主迭代阶段”、按何种节奏合并开发提交至 `main`，以及是否授权启动小范围首批外部用户试跑。在获得明确口头/书面放行前，绝不越线执行任何真人测试动作。
