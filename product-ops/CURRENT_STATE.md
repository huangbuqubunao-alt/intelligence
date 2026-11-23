# 当前运营与恢复状态（CURRENT_STATE）

- **最后更新**：2026-11-23（`Asia/Shanghai` · Iteration #8 / `BL-011` 分支验收集齐，待创始人 L3 裁决是否合流 `main`）
- **当前运行阶段**：**内部自主迭代与产品完善阶段**（严禁招募、联系或组织真实外部用户测试）
- **当前工作分支**：`antigravity/task-user-readiness-20261112`（含 Iteration #8 `BL-011` 按需轻量关键帧融合分析 MVP 及第 13 组 CI 接线，**尚未合流 `main`**）
- **最新公开主线基线（`main` & `origin/main`）**：`c15cf06`（已按 `FD-006` 同步至 Iteration #7 + 12 组 CI 接线 `aec26da`；GitHub Actions [`Public Beta CI #45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845) 双端 `success`：`Frontend Build & Vitest` `1m43s` + `Python Lint, Typecheck & Public Beta Integration` `4m42s` / `146 passed`；仓库保持 `PUBLIC` 被动状态，零外宣、零 Release Tag、Stars `0`、Forks `0`、Open Issues `1` 仅历史 `#4`）

---

## 核心运行状态快照

- **当前产品目标**：在内部完善阶段把“跨平台核验 → 诚实拒答 → Obsidian 深链导出”主航道的冷启动首用体验、双语界面一致性、跨源评测确定性、>500 资料库与 4h/300KB 长媒体文档边界、以及真实 Obsidian `.zip` 导出稳定性全部打磨至零 P0/P1 摩擦。
- **最近已完成的关键工作**：
  1. **执行 `FD-005` 创始人裁决（`main@f23954f`）**：保留仓库 `PUBLIC` 被动状态并严守零推广、零招募、`EXP-001` 维持 `HOLD`；将 Iteration #3 已验证提交同步至 `main` 并推送 `origin main`，实测 GitHub Actions `#45149288840` 双作业绿灯（Frontend `1m43s` + Python `3m14s`）。
  2. **完成 Iteration #4–#6（`6760028` / `2be958f` / `dbc7e89` — `BL-005`..`BL-008`）**：交付 `/evidence` 快读（`39.6ms`）+ 双层详情栏、32 例 Eval、可跳转三步引导与缺失中文化（`54/54` Vitest + 双主题 Chromium 全通）、600 条库向后兼容分页/跨库问答 `0.23s`/SQLite `.backup()` 零密钥热快照 `5.5ms`、`COLD /videos` `68.56ms`（3.5x）与 `#Settings` 零扰动复审。
  3. **完成 Iteration #7（`BL-010`）与 `FD-006` 主线 CI 合流（`main@c15cf06`）**：
     - 修补 5 项高隐蔽导出与采样缺陷（UTF-8 `<=180B`、Windows `_CON`、大小写碰撞、全量 YAML 转义、空行恢复与文本禁 `00:00`、`>4,000` 字均匀采样），并将 `test_long_media_and_obsidian_vault.py` 纳入 `ci.yml` 合并至 `main@c15cf06`，GitHub Actions [`#45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845) 双端绿灯通过（`1244/1244` 前端 + `146/146` 后端）。
  4. **完成 Iteration #8（`BL-011` · 研发分支待合流 `main`）**：按需轻量本地视频关键帧抽取 + 64 位 dHash 去重 + 原话字幕时间对齐融合分析 MVP 落地，默认 `$0` 本机 Ollama（`409 LOCAL_VISION_MODEL_UNSUPPORTED` 防盲发）并严格复用 BYOK 安全/日预算限额与原子防覆写暂存；支持前端双主题图卡筛选、Lightbox 键盘导航（`ArrowRight`/`Escape`）、单视频 `visual-pack.zip` 及全库 `obsidian-bundle.zip` `assets/*.jpg` 打包与 Sidecar 备份恢复，零核心 `state.sqlite3` Schema 变更。
- **质量验收快照（Iteration #8 分支实测 + `main@c15cf06` 云端对照）**：
  - 后端本地（Iteration #8 最终改动后）：`ruff check` 0 错、`mypy src`（137 文件）0 错、13 组完整 CI `pytest` 独跑 **`151 passed in 367.69s (0:06:07)`**（0 failed, 0 skipped，含新增 `test_visual_keyframe_analysis.py` 真实 `ffmpeg` / `.zip` 验证）、Backup/Restore 专项 **`27 passed in 39.46s`**、`scripts/security_scan.sh` 无新增命中；
  - 前端本地（Iteration #8 最终改动后）：`npm run build`（`875ms`）零报错、全量 Vitest **`Test Files 55 passed (55) / Tests 1247 passed (1247)`**（耗时 `63.51s`，含新增 `WorkspaceVisualKeyframes.test.tsx`）；
  - 本机真视觉模型 & 实机浏览器 E2E：真实 `ollama/gemma3:4b`（`$0`）对 5 段多场景 `.mp4` 成功抽取 4 去重帧并识别 3 信息帧与中文融合洞察；隔离服务 `127.0.0.1:8796` Chromium 实机验证 Obsidian Dark `1440×900` 与 Warm Paper Light `375×812`、筛选、`ArrowRight`/`Escape` Lightbox、`visual-pack.zip`（`200`, `7826B`）、空态与纯文本隐藏门禁全通（`0` console error / `0` HTTP `>=400` / `0px` 横向溢出）；
  - 云端 Ubuntu Linux CI 对照（`main@c15cf06` / `aec26da`, [`#45187713845`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45187713845)）：双作业 `success`（`1244/1244` 前端 + 12 组 `146/146` 后端），本次 Iteration #8 分支尚未推合 `main`。
  - 真实外部用户数据与留存：**`当前不可评估`**（内部阶段严格遵守零真人测试边界）。
- **待创始人 L3 决策（PENDING）**：
  - **暂无阻塞性内部执行审批项（`Pending Founder Decisions: 0`）**；Iteration #8（`BL-011`）已在研发分支完整验收就绪，是否批准按 L3 权限将 Iteration #8 + 第 13 组 CI 接线合流 `main` 由创始人裁定（`EXP-001` 真人试验继续 `HOLD`）。
- **下一步安全可执行动作（中断恢复指引）**：
  1. 若创始人批复批准将 Iteration #8 合流 `main`，线性合入并验证 GitHub Actions 13 组 CI 云端绿标，严守被动 `PUBLIC`、零外宣、零 Release Tag 与 `EXP-001` 维持 `HOLD`；
  2. 持续维护 `product-ops/` 与每晚 21:00 CPO 日报巡检。
