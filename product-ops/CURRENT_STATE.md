# 当前运营与恢复状态（CURRENT_STATE）

- **最后更新**：2026-11-24（`Asia/Shanghai` · **Iteration #10 / `BL-013` Round 2 完成 Claude 初审 `Conclusion B` 全部 `N1`–`N11` 闭环修复，待二轮复核后裁决 `FD-009`**）
- **当前运行阶段**：**内部自主迭代与产品完善阶段**（严禁招募、联系或组织真实外部用户测试）
- **当前工作分支**：`antigravity/task-user-readiness-20261112`（已在 `c16f0e8` 基础上完成 Claude Round 1 复核全部 11 项发现 `N1`–`N11` 的修复与后端/Vitest 全绿验证；待 Claude Round 2 复核及创始人 `FD-009` 批复，未合入 `main`、未推送）
- **最新公开主线对照基线（`main` & `origin/main`）**：`ca4e17f`（对应 Iteration #9 / `BL-012` 收口，[`#45219985703`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45219985703)，仓库保持 `PUBLIC` 被动状态，零外宣、无 GitHub Release、本轮未新增发布标签、保留 4 个历史 tag、`Stars: 0`、`Forks: 0`）

---

## 核心运行状态快照

- **当前产品目标**：关闭 Claude 独立复核（Round 1 `Conclusion B`）指出的 3 项 P1 阻断与 8 项 P2 问题（`N1`–`N11`），完成静态/全量单测集成验证后交由 Claude Round 2 独立复核，决定是否批准 `FD-009` 合流 `main`。
- **最近已完成的关键工作**：
  1. **执行 `FD-005` ~ `FD-008` 主线同步（至 `main@ca4e17f`）**：Iteration #1–#9 依次获批合入 `main` 且严守被动 `PUBLIC`、零外宣与 `EXP-001` `HOLD`。
  2. **完成 Iteration #10（`BL-013` Round 1，`c16f0e8`）+ Round 2 缺陷修复（`N1`–`N11`）**：
     - **Round 1（`c16f0e8`，对应 Codex 审查 15 P1 + 7 P2）**：实现混合无据剥离、单段 `TEXT_RANGE` 绑定、`NEEDS_REVERIFICATION` 复核、Demo 混合拒答、CJK 2-gram FTS5、`?evidence_id=` 尾段直达、BYOK 禁止重定向、`64 MiB` 恢复 + SHA-256 `40 MiB` 离线图包、原子视觉目录切换 + `dir_fd` `O_NOFOLLOW`、`BEGIN IMMEDIATE` 预算扣减、`#Content` 200+ 分页与 `?q=` / `⌘K` 全库与清锁、以及 `include_markdown=False` 列表加速；随后 Claude 独立复核给出 **Conclusion B**（指出 `N1`–`N11` 共 3 P1 + 8 P2 剩余缺口，暂缓合流）。
     - **Round 2（本轮关闭 `N1`–`N11`）**：
       - **P1 阻断关闭（`N1`–`N3`）**：`N1` 加固 `[E88]`/`【E77】`/`[ E88 ]`/`[E88,E1]`/`(E88)`/裸 `E88` 全变体识别，要求混合长句仅保留带真实有效引用且含实质论据的子句，并彻底清除未佐证悬空断言与引用存根；`N2` 修复恢复记录与整库 Vault / `.zip` 导出在未通过主库复核时强制重建带 `NEEDS_REVERIFICATION` 告警头与 `[待核验]` 标记的 Markdown（绝不原样吐出未经核验备份正文）；`N3` 为 `export_backup_snapshot` 补齐 `40 MiB` 关键帧预算降级（`VISUAL_BUDGET_EXCEEDED`）与 `64 MiB` JSON 体积总上限裁剪（`BACKUP_SIZE_BUDGET_EXCEEDED`），超限场景记录 `skipped_visual_assets` 与 `warnings` 同时完整保住摘要/问答/配置且保证导出的快照可成功恢复；
       - **P2 缺口与台账同步（`N4`–`N11`）**：`N4` 移除纯文本提炼失败回退首段的错误绑定并明确标为未核验；`N5` 移除 Demo 混合前提 `0.65` 放行阈值与误删字素并校验连续跨度；`N6` 优先调用 Ollama `/api/show` 探测能力并移除 `start` 预检前 8 个模型截断；`N7` 补齐单视频关键帧分析串行锁与跨提交后旧 `gen-*` 目录回收；`N8` 移除 `_STDLIB_URLOPEN` 测试后门改由统一 `_NoCloudRedirect` 派发；`N9` 增加双 Hub 实例并发多线程每日预算竞争验证；`N10` 补全 `#Content` 搜索结果分页加载（`>100` 条）与 `⌘K` 命中截断总条数提示；`N11` 恢复 `product-ops/reports/daily/2026-11-23.md` 历史日报基线至 `8e63e04` 并修正 CI 历史记录与本轮验证边界说明。
- **质量验收快照（Round 2 `N1`–`N11` 最终改动后实测）**：
  - 后端：`uv run ruff check --no-cache src tests scripts` 0 错、`uv run mypy --no-incremental --cache-dir=/dev/null src`（137 文件）0 错；14 组 CI + 2 组备份/恢复共 **16 组 Python 套件 `200 passed in 595.70s (0:09:55)`**（`0 failed`, `0 skipped`，含 `test_codex_review_remediation.py` `21/21`）；
  - 前端：`cd frontend && npm run build`（`vite build` `770ms`）零报错、全量 Vitest **`Test Files 57 passed (57) / Tests 1257 passed (1257)`**（耗时 `55.92s`，`0 failed`, `0 skipped`，含 `CodexReviewRemediation.test.tsx` `8/8`）；
  - 未覆盖边界（明确披露）：Round 2 改动后**未重跑** Chromium 实机 E2E（上一轮实机证据停留在 Round 1 `c16f0e8` 隔离 `8794` 端口）、未实测 Windows WSL2、未连接真实云/本地大模型，且云端 CI 仍对应 `main@ca4e17f`（Round 2 尚未上云）；
  - 真实外部用户数据与留存：**`当前不可评估`**（内部阶段严格遵守零真人测试边界）。
- **待创始人 L3 决策（PENDING）**：
  - **`FD-009`（PENDING — 待 Claude Round 2 复核无阻断后裁决是否合流 `main` 并触发云端 14 组 CI）**：`EXP-001` 与 `BL-009` 继续维持 `HOLD`，仓库维持被动 `PUBLIC`、零外宣、无 GitHub Release。
- **下一步安全可执行动作（中断恢复指引）**：
  1. 在 `antigravity/task-user-readiness-20261112` 提交 Round 2 修复并交给 Claude 执行二轮独立复核；
  2. 待 Claude 复核转结论 A 后再呈请创始人终审 `FD-009` 合流 `main`，严守被动 `PUBLIC`、零外宣、无 Release 与零真人试验边界。
