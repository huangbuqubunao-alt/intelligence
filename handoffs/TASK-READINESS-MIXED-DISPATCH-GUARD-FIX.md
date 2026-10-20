# TASK-READINESS-MIXED-DISPATCH-GUARD-FIX 实现交接

## 元数据

- 任务：`TASK-READINESS-MIXED-DISPATCH-GUARD-FIX`（Role Implementer）
- 日期：2026-10-20，Asia/Shanghai。
- Base（拒收候选）：`d9226ff607a211f2e7dc196e9f447fdaea31bca1`（UI `9927324`、核心 `19d8107`）。
- Worktree：`/Users/hua/Documents/yia-worktrees/readiness-mixed-dispatch-guard-fix`；branch `codex/task-readiness-mixed-dispatch-guard-fix`。
- 最终 commit：见本文提交记录；commit 后 cleanSTOP。

## 目标复述与本轮修复

- Reviewer 独立确认的 P1：d9226ff 把 `inputRefresh` 加进 `DeepAnalysisPanel`
  清除 `dispatchBlocked(false)` 的同一个 effect（App.tsx 原行 2186）。已授权
  云投递结果未知时字幕 SUCCEEDED 刷新会重新启用 "Run Deep Analysis"。
- 修复（最小两行）：该 effect 只保留 `setPreflight(null)` 与
  `setCostAcknowledged(false)`（依赖 `[videoId, inputRefresh]`，保持既有
  preflight/费用确认失效语义与 GET 重读）；`dispatchBlocked(false)` 移入
  仅依赖 `[videoId]` 的独立 effect，保持原有导航清除语义。同 Content 的
  字幕成功刷新永不重置未知云投递保护；不新增 POST、不自动重试、不推断旧
  投递已终止、不弱化费用/资格门。

## 改动文件（全量 diff 复核完毕）

1. `frontend/src/workspace/App.tsx`：仅上述 effect 拆分（+2/−1）。
2. `frontend/src/workspace/App.dispatch-caption-guard.test.tsx`：新增，4 例。

## 测试（mock 仅 frontend，无真实网络/模型/自动 POST）

- 红：原 reviewer 反例原样保留，`expect((run).disabled, "a caption refresh
  must not clear an ambiguous cloud dispatch").toBe(true)` 原字重现；修复前
  FAIL（expected false to be true）。
- 绿：修复后同反例 PASS。新增配套：
  1. 同 Content 输入刷新期间残留过期 preflight 仅被清除、费用确认重置、
     blocked 状态保持；preflight 前后计数 1→2、executions=1。
  2. 相同成功 token 的重复读取不循环：deepReads 保持 2、executions=1、
     Run 保持禁用（evidence 增量全部来自显式读取按钮，为既有语义）。
- 完整 frontend：**968 PASS / 37 files / 0 fail**（基线 964 恰好 +4 新例，
  既有测试零改动、零跳过、零弱化）。
- `npm run typecheck` PASS；`npm run build` PASS；`git diff --check` PASS。
- 本切片无 Python 改动 → Ruff 及后端全量按任务卡未跑（后端无变更）。

## 证据

- `docs/validation/end-to-end-user-readiness/MIXED_DISPATCH_GUARD_FIX_IMPLEMENTER_2026_10_20.json`
  （含逐项 SHA256：源文件与红/绿/全量/typecheck/build 日志，均在 worktree
  `.var/dispatch-guard/`，忽略目录，是否保留由 root 决定）。
- Reviewer 反例逐字保留于 `"keeps an unknown cloud dispatch blocked when a
  verified caption result arrives"`用例。

## 复用决策

- DIRECT：现有 `App` 状态/invalidation 结构、既有 vitest/testing-library
  工具与 mock fixture 约定、task 卡引用的独立反例作为测试素材。无新增
  依赖、无第三方源码引入。

## 范围外/未做

- 未动 backend、state、transcripts、Schema、依赖、凭据、资格、frozen
  stock、owner/正式数据；未更新公共看板；未合并 main。
- Root 真实 GUI 备份恢复在旧候选上仅证明 Backup 部分；mixed 整体接受
  仍需本 P1 修复的独立审查 APPROVE + 累积候选整合与真实 GUI 复验。

## 状态

- 本交接仅声明实现完成并可供独立审查；不宣布任务 DONE。
