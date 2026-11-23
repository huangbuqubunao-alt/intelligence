# 当前运营与恢复状态（CURRENT_STATE）

- **最后更新**：2026-11-23（`Asia/Shanghai`）
- **当前运行阶段**：**内部自主迭代与产品完善阶段**（严禁招募、联系或组织真实外部用户测试）
- **当前工作分支**：`antigravity/task-user-readiness-20261112`（完成 Iteration #6 `BL-008`：基于 `2be958f` 落地 >500 大库分页/全库分块检索与 SQLite `.backup()` 零密钥热快照，并完成冷读提速与 `#Settings` 零扰动复审）
- **最新公开主线基线（`main` & `origin/main`）**：`f23954f9f1f7922ce626e3bbdafe4ee2d8ca01aa`（已按 `FD-005` 批准完成合流；GitHub Actions [`Public Beta CI #45149288840`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45149288840) 双端 `success`；仓库保持 `PUBLIC` 被动状态，零外宣、零 Release Tag、Stars `0`）

---

## 核心运行状态快照

- **当前产品目标**：在内部完善阶段把“跨平台核验 → 诚实拒答 → Obsidian 深链导出”主航道的冷启动首用体验、双语界面一致性、跨源评测确定性与 >500 条资料库扩展性打磨至零 P0/P1 摩擦。
- **最近已完成的关键工作**：
  1. **执行 `FD-005` 创始人裁决（`main@f23954f`）**：保留仓库 `PUBLIC` 被动状态并严守零推广、零招募、`EXP-001` 维持 `HOLD`；将 Iteration #3 已验证提交同步至 `main` 并推送 `origin main`，实测 GitHub Actions `#45149288840` 双作业绿灯（Frontend `1m43s` + Python `3m14s`）。
  2. **完成 Iteration #4–#5（`6760028` / `2be958f` — `BL-006` / `BL-005` / `BL-007`）**：`/evidence` 单快照快读冷启动 `39.6ms` + SWR 防闪烁与双层动作栏，离线 Eval 扩至 `32/32`，首轮三步引导与缺失中文化全量落地（`54/54` Vitest + 双主题桌面/移动 Chromium 验证全过）。
  3. **完成 Iteration #6（`BL-008` — >500 大库可扩展性、热快照与 `#Settings` 零扰动复审）**：
     - 全库扩展与向后兼容分页：`list_videos(*, limit=200, offset=0)`、`count_videos*` 与 `list_all_videos*` 替换 `WorkspaceIntelligenceHub` 全部 8 处 `300`/`500` 上限；`GET /api/v1/videos?limit=&offset=` 在 Raw 与 Fast API 保持字节与 `400 INVALID_QUERY` 校验一致，无参数请求保持零破坏兼容；
     - 在线 SQLite `.backup()` 热快照与冷读提速：新增 `create_sqlite_hot_snapshot()`（`hub-snapshot.sqlite3`，`0o600`，`PRAGMA integrity_check == "ok"`，零密钥），并完成源信号 4 列轻量化投影、单次 DA 路由解析与复用目录指纹的未篡改摘要内存索引，压测 `COLD /videos` `243.42ms -> 68.56ms`、`COLD /intelligence` `48.92ms -> 21.90ms`；
     - `#Settings` 零扰动复审：确认 `#settings-legacy-diagnostics` 在 `hasWorkspaceAi === true` 时已默认折叠收起，本轮零前端改动（`DEC-OPS-009`）。
- **质量验收快照（Iteration #6）**：
  - 后端（Iteration #6 最终改动后）：`ruff` 0 错、`mypy` 136 文件 0 错、`11` 组 CI `pytest` 独跑 **143/143 passed in 505.13s**（含 600 条大库分页/全库问答 `0.23s`/热快照 `5.5ms` 与 32 例 Eval）、`test_v1x_phase1b_backup_restore.py` + `test_research_backup_restore.py` **27/27 passed in 59.89s**；
  - 前端（承接 Iteration #5 `2be958f`，Iteration #6 零 `frontend/` 改动）：`npm run build`（`3.23s`）零报错、全量 Vitest **54/54 文件 / 1244/1244 tests passed in 88.35s**；Chromium `1440×900` Obsidian Dark 与 `375×812` Warm Paper Light 三步引导与跳过空首页实机全通（0 溢出 / 0 报错）。
  - 真实外部用户数据与留存：**`当前不可评估`**（内部阶段严格遵守零真人测试边界）。
- **待创始人 L3 决策（PENDING）**：
  - **暂无待决策项（`0 PENDING`）**（`FD-005` 已执行闭环）。
- **下一步安全可执行动作（中断恢复指引）**：
  1. 维持 `antigravity/task-user-readiness-20261112`（含 Iteration #4–#6 成果）于独立研发分支，后续按阶段节奏视需要提请创始人 L3 合流 `main`；继续开展隔离环境下的长视频/多轮导入边界自查及 Week 3 退出检查单准备；
  2. 每天 21:00 维持 CPO 日报自动巡检，严守零推广、零外放与零真人测试红线。
