# 当前运营与恢复状态（CURRENT_STATE）

- **最后更新**：2026-11-24（`Asia/Shanghai` · **Iteration #11 / `BL-014`：Codex Round 2 全量闭环完成、`995` 份历史文档脚本当前工作树隐私脱敏、CI 扩充至 `7,124` 项 Python 测试与真实 `qwen3.5:9b` `EXP-002` 100% 逐句/要点引用复验完毕，研发分支待创始人审批合流 `main`**）
- **当前运行阶段**：**内部自主迭代与产品完善阶段**（严禁招募、联系或组织真实外部用户测试）
- **当前工作分支**：`antigravity/task-user-readiness-20261112`（含 Iteration #11 / `BL-014` 全部修复、脱敏、扩展 CI 与实测成果；待创始人审阅并裁决合流 `main`）
- **最新公开主线基线（`main` & `origin/main`）**：`d1b58f7`（仅文档收口同步提交，对应已通过云端 CI [`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) 的代码提交为 `main@4f3fe70`；仓库保持 `PUBLIC` 被动状态，零外宣、无 GitHub Release、本轮未新增发布标签、保留 4 个历史 tag、`Stars: 0`、`Forks: 0`）

---

## 核心运行状态快照

- **当前产品目标**：完成 Codex Round 2 审查提出的全量产品可信度、安全边界、大库性能、当前树隐私脱敏与 CI 全仓覆盖闭环，提交研发分支供创始人裁决是否开展独立复核或合流 `main`。
- **最近在研发分支已完成的关键工作（`antigravity/task-user-readiness-20261112`）**：
  1. **防幻觉、Demo 边界与本机模型实测再加固（`P0-1`、`P2-1` + `ce6f8dcc`）**：全角/小写/空格 `[E*]` 变体、布尔伪装 `"answerable": "false"`、内联列表、Markdown 表格行逐句清洗，历史回读/恢复前统一剪枝；Demo 修复「多少钱」与反向否定前提假问答并保留 UI 胶囊可用性；修正要点/行动建议跨句引用自动水合缺口后，本机真实 `ollama/qwen3.5:9b`（`$0` 云花费）重跑 `EXP-002` 达成 **3/3 `GROUNDED` + 2/2 拒答 + 13/13 (100%) 逐句引用 + 18/18 (100%) 要点行动引用**（`out_of_range_refs=0`）。
  2. **大库稳定性、恢复事务化、SSRF/Proxy 安全与编码兼容（`P1-1`、`P1-2`、`P1-3`、`P2-2`–`P2-10`、`P2-13`）**：`list_research_sessions()` 轻量查询 + 单事务批量核验 + LRU 缓存（600 会话 `<300ms`）；只读 `.as_uri()` 修正特殊路径字符；原子写回与精确 `422 RESTORE_INVALID_PAYLOAD` 错误码；全形式 SSRF（十进制/十六进制/DNS 重绑定/`nip.io`/`CGNAT`）、`4 MiB` 响应封顶与回环直连绕过 `http_proxy`；支持 GB18030/UTF-16 本地笔记且 `verify_source` 同步兼容；前端解除 2s 轮询对第 2 页/搜索状态重置、清除过期 `⌘K` 计数并隔离 Demo 引导状态；`/api/v1/dashboard` 无 Sidecar 一致性修复。
  3. **当前工作树隐私脱敏与全仓 CI 扩容（`P1-4`、`P2-11`、`P2-12` 选项 B）**：在不重写 Git 历史前提下对 `995` 份历史追踪文档与脚本完成本机目录/邮箱/主机名脱敏（`git grep` 零残留，`security_scan.sh` 对 `src/`/`frontend/`/`scripts/`/`product-ops/` 均 `0` 告警）；`.github/workflows/ci.yml` 保留 14 组核心公开子集并新增 `tsc --noEmit`、4 分片 `python-unit-full`（`3,955` 项）及 8 分片 `python-integration-full`（`3,169` 项），合计 **`7,124` 项 Python CI 覆盖**（并在 `docs/RELEASE_CHECKLIST.md` 明确披露 `GOV-001` 与外部 worktree 夹具）；前端默认并发 Vitest **`57/57` / `1,259/1,259 passed`（`65.21s`）** 及稳定性 10/10 全绿；`product-ops/reports/daily/2026-11-23.md` 与 `8e63e04` 完全一致。
- **质量验收快照（`antigravity/task-user-readiness-20261112` 分支本地实测）**：
  - 静态：`ruff check --no-cache src tests scripts` 0 错；`mypy --no-incremental --cache-dir=/dev/null src`（137 文件）0 错；
  - 后端：`14 组` Public Beta 子集 `181 passed in 686.65s`（`ce6f8dcc` 补充回归复测 `32 passed in 127.76s`）；Unit 4 分片 `3,954 passed, 1 skipped, 2 deselected`；Integration+E2E+Scripts 4 分片 `3,166 passed` + 隔离 `test_fast_read_api.py` `2/2`；
  - 前端：`tsc --noEmit` + `vite build` `1.38s` + 默认 `npx vitest run` **`57/57` / `1,259/1,259 passed`** + 10/10 连续稳定性通过；
  - 已公开 `main@d1b58f7` 前置代码（`main@4f3fe70`）保持云端 [`#45339507823`](https://github.com/huangbuqubunao-alt/intelligence/actions/runs/45339507823) 绿标；真实外部用户数据：**`当前不可评估`**（`EXP-001` 维持 `HOLD`）。
- **待创始人 L3 决策（PENDING）**：
  - **是否将当前研发分支 `antigravity/task-user-readiness-20261112` 线性合流 `main` 并触发云端全仓（`7,124` Python + `1,259` Vitest）Actions 验收，或先安排独立 Codex/Claude 复核**（`EXP-001` 与 `BL-009` 继续维持 `HOLD`）。
- **下一步安全可执行动作（中断恢复指引）**：
  1. 维持分支干净状态与 `main@d1b58f7` 零越权改动，严守被动 `PUBLIC`、零外宣、无 GitHub Release 与零真人试验边界；
  2. 根据创始人回复执行分支合流 `main` 或配合第三方复核。
