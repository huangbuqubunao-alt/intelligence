# 当前运营与恢复状态（CURRENT_STATE）

- **最后更新**：2026-11-23（`Asia/Shanghai`）
- **当前运行阶段**：**内部自主迭代与产品完善阶段**（严禁招募、联系或组织真实外部用户测试）
- **当前工作分支**：`antigravity/task-user-readiness-20261112`（完成 Iteration #4 `BL-006` + `BL-005` 闭环）
- **最新公开主线基线（`main` & `origin/main`）**：`f23954f9f1f7922ce626e3bbdafe4ee2d8ca01aa`（已按 `FD-005` 批准完成合流；GitHub Actions [`Public Beta CI #45149288840`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45149288840) 双端 `success`；仓库保持 `PUBLIC` 被动状态，零外宣、零 Release Tag、Stars `0`）

---

## 核心运行状态快照

- **当前产品目标**：在内部完善阶段把“跨平台核验 → 诚实拒答 → Obsidian 深链导出”主航道的冷启动体验、内容详情阅读密度、跨源评测确定性与工程质量覆盖磨平至零 P0/P1 摩擦。
- **最近已完成的关键工作**：
  1. **执行 `FD-005` 创始人裁决（`main@f23954f`）**：保留仓库 `PUBLIC` 被动状态并严守零推广、零招募、`EXP-001` 维持 `HOLD`；将 Iteration #3 已验证提交同步至 `main` 并推送 `origin main`，实测 GitHub Actions `#45149288840` 双作业绿灯（Frontend `1m43s` + Python `3m14s`）。
  2. **完成 Iteration #4 — `BL-006` 内容详情快读与界面减负**：
     - 后端 `fast_read_api.py` 补齐 `/api/v1/videos/<id>/evidence` 单快照快读缓存与详情/证据同口令投影，Demo 实测 `/evidence` 响应从 **`583–713ms` 降至 `39.6ms`（冷读）/ `3.8–5.8ms`（热缓存）**；
     - 前端 `ContentEvidencePanel` 开启 SWR 缓存与刷新保留（`retainOnRefresh`），彻底消除详情首次展开与精选切换时的加载闪烁；
     - `WorkspaceVideoAiActions` 重构为主/次双层动作栏，并在移动端 `<=768px` 自动隐藏键盘快捷键提示，桌面与手机视图排版清晰且保持 100% 既有功能入口。
  3. **完成 Iteration #4 — `BL-005` 反幻觉评测扩容与 Demo 拒答加固**：
     - `test_grounding_refusal_eval.py` 由 20 例扩充至 **`32` 例**，覆盖双语多源冲突对照、时序段落锚点及越界/时序伪造拒答；
     - `demo_showcase.py` 加固英文复数词干归一化与产品框架停用词过滤，消除“借产品泛词绕过拒答门禁”隐患。
- **质量验收快照（Iteration #4）**：
  - `ruff` 0 错、`mypy` 136 文件 0 错；
  - `11` 组 CI `pytest` 合跑 **141/142**（唯一超时项 `test_fast_read_api.py:448` 在并发争抢下耗时 `217.6ms`）+ 无 `.py` 修改单独复跑 `test_fast_read_api.py` **2/2 passed in 210.42s**（完整覆盖 142 项测试，含 `32/32` Eval）；
  - `npm run build`（最终 CSS 修改后 `2.36s`）成功、Vitest **54/54 文件 / 1241/1241 tests passed**（最终 CSS 调整前全量跑通，随后以 `vite build` + Chromium 移动端复检闭环）；
  - Chromium `1440×900` & `375×812` 实机复检 `0` console errors、`0` HTTP `>=400`、`0px` 横向溢出、9 条原文证据瞬时呈现。
  - 真实外部用户数据与留存：**`当前不可评估`**（内部阶段严格遵守零真人测试边界）。
- **待创始人 L3 决策（PENDING）**：
  - **暂无待决策项（`0 PENDING`）**（`FD-005` 已执行闭环）。
- **下一步安全可执行动作（中断恢复指引）**：
  1. 在 `antigravity/task-user-readiness-20261112` 继续推进 **`BL-007`**（P2 精简 `#Settings` 三栏次级信息与实验开关层级视觉，保持功能契约零退化），Iteration #4 暂留开发分支按里程碑批量同步；
  2. 每天 21:00 维持 CPO 日报自动巡检，持续跟踪公开竞品动态与零外宣前提下的核心体验收敛。
