# 当前运营与恢复状态（CURRENT_STATE）

- **最后更新**：2026-11-23（`Asia/Shanghai` · `FD-006` `main` 合流与云端 CI 验收完成）
- **当前运行阶段**：**内部自主迭代与产品完善阶段**（严禁招募、联系或组织真实外部用户测试）
- **当前工作分支**：`antigravity/task-user-readiness-20261112`（完成 Iteration #4–#7 与 `.github/workflows/ci.yml` 12 组全量 CI 接线 `028d10e`，并按 `FD-006` 同步至 `main`）
- **最新公开主线基线（`main` & `origin/main`）**：`aec26da2190a235f03be0b0013080b76b06c5b15`（已按 `FD-006` 批复同步 Iteration #4–#7 + 12 组 CI 接线；GitHub Actions [`Public Beta CI #45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845) 双端 `success`：`Frontend Build & Vitest` `1m43s` + `Python Lint, Typecheck & Public Beta Integration` `4m42s` / `146 passed`；仓库保持 `PUBLIC` 被动状态，零外宣、零 Release Tag、Stars `0`、Forks `0`、Open Issues `1` 仅历史 `#4`）

---

## 核心运行状态快照

- **当前产品目标**：在内部完善阶段把“跨平台核验 → 诚实拒答 → Obsidian 深链导出”主航道的冷启动首用体验、双语界面一致性、跨源评测确定性、>500 资料库与 4h/300KB 长媒体文档边界、以及真实 Obsidian `.zip` 导出稳定性全部打磨至零 P0/P1 摩擦。
- **最近已完成的关键工作**：
  1. **执行 `FD-005` 创始人裁决（`main@f23954f`）**：保留仓库 `PUBLIC` 被动状态并严守零推广、零招募、`EXP-001` 维持 `HOLD`；将 Iteration #3 已验证提交同步至 `main` 并推送 `origin main`，实测 GitHub Actions `#45149288840` 双作业绿灯（Frontend `1m43s` + Python `3m14s`）。
  2. **完成 Iteration #4–#6（`6760028` / `2be958f` / `dbc7e89` — `BL-005`..`BL-008`）**：交付 `/evidence` 快读（`39.6ms`）+ 双层详情栏、32 例 Eval、可跳转三步引导与缺失中文化（`54/54` Vitest + 双主题 Chromium 全通）、600 条库向后兼容分页/跨库问答 `0.23s`/SQLite `.backup()` 零密钥热快照 `5.5ms`、`COLD /videos` `68.56ms`（3.5x）与 `#Settings` 零扰动复审。
  3. **完成 Iteration #7（`BL-010`）与 `FD-006` 主线 CI 合流（`main@aec26da`）**：
     - 修补 5 项高隐蔽导出与采样缺陷：`<=180B` UTF-8 安全文件名防止长中文解压报错、`CON` 等 Windows 保留字加前置下划线、`used_paths_lower` 大小写不敏感防覆盖、全部 5 处 Frontmatter 安全 YAML 转义、视频/周报空行恢复及文本笔记不再误标 `00:00` 假时长，并将 `>4,000` 字 Markdown 摘要升级为全篇均匀多锚点采样（0%–96%+）；
     - 新增隔离端到端专项测试 `test_long_media_and_obsidian_vault.py`（4h 讲座 `03:52` 溯源 + `>300KB`/`2900` 行文本 tail 召回 + `.zip` 落盘实解压 & `yaml.safe_load` 全过）并正式纳入 `.github/workflows/ci.yml`（`028d10e`）；按创始人 **`FD-006`** 批复同步至 `main@aec26da`，GitHub Actions [`#45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845) 双端绿灯通过（`1244/1244` 前端 + `146/146` 后端）。
- **质量验收快照（`main@aec26da` 云端 + 本地实测）**：
  - 云端 Ubuntu Linux CI（[`Public Beta CI #45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845) @ `aec26da`）：`Frontend Build & Vitest` `1m43s`（`vite build` `1.52s` + `54/54` / `1244/1244` tests passed）；`Python Lint, Typecheck & Public Beta Integration` `4m42s`（`ruff`/`mypy` 0 错 + 12 组全量套件 **`146 passed in 231.25s`**，含 `test_long_media_and_obsidian_vault.py`）；
  - 后端本地（Iteration #7 最终代码后）：`ruff` 0 错、`mypy` 136 文件 0 错、`test_long_media_and_obsidian_vault.py` **3/3 passed in 19.04s**、`11` 组 CI `pytest` 独跑 **143/143 passed in 437.61s**（`0 failed`, `0 skipped`）；关联备份恢复专项 `test_v1x_phase1b_backup_restore.py` + `test_research_backup_restore.py` 于 `dbc7e89` 实测 `27/27 passed`；
  - 前端本地（承接 Iteration #5 `2be958f`，Iteration #6–#7 零 `frontend/` 改动）：`npm run build`（`3.23s`）零报错、全量 Vitest **54/54 文件 / 1244/1244 tests passed in 88.35s**；Chromium `1440×900` Obsidian Dark 与 `375×812` Warm Paper Light 三步引导与跳过空首页实机全通。
  - 真实外部用户数据与留存：**`当前不可评估`**（内部阶段严格遵守零真人测试边界）。
- **待创始人 L3 决策（PENDING）**：
  - **暂无阻塞性审批项（`0 PENDING`）**（`RELEASE_READINESS_GATE.md` 与 `FD-006` 主线同步均已完成；是否推进下一轮选定能力或开启 `EXP-001` 由创始人单独决定）。
- **下一步安全可执行动作（中断恢复指引）**：
  1. 内部核心主航道与长媒体/导出边界已在 `main@aec26da` 达成 **Internal Exit Ready**：严守 `FD-005`/`FD-006` 零推广、零招募与零真人试验边界；按创始人对未完成/暂缓清单（含按需关键视频帧结合分析、Round 19 细节打磨等）的选型指示进入下一轮小步迭代；
  2. 每天 21:00 维持 CPO 日报自动巡检与增量市场/竞品监控。
