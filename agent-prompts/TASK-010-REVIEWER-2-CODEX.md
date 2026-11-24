# TASK-010 Correction 1 — 第二位独立 Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-010 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-010.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：动态读取 `git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-010-REVIEWER-2-CODEX.md`；main 中 TASK-010 必须为 `IN_REVIEW`。
- Source/base：`/Users/developer/Documents/yia-worktrees/task-010` /
  `codex/task-010-orchestration-recovery@b4c97bed2d3f44a24eb2550f9fb43cc381661264` /
  `227bdeba3a4d9ddd57231b123bfdc4a2038af3d3`。
- Correction 1 唯一父为 reviewer-1 evidence `f929a2f114626f7f714134d0894b188548537e4e`；完整允许范围仍严格为 pipeline/jobs/retry、两份集成测试与 handoff，Correction 1 本身只可改 pipeline、两份测试和 handoff。

## 洁净度与强制审查

开始时 source 必须干净，不得运行会写入 `.codebase-memory/` 的索引动作。用已配置的 codebase-memory MCP（必要时再用 CodeGraph）做窄范围只读定位，核验父链、完整 Diff、Correction 范围和所有离线门禁。

独立复跑 lock check、locked sync、两份 TASK-010 集成测试、全量 pytest、mypy、Ruff、CLI help、offline build、sdist/wheel migration/template inclusion 与固定 `git diff --check`。

在 pytest 临时 SQLite/离线 Fake 中独立验证：

1. 真实 `RepositoryBackedAnalysisService` 的 `AnalysisCompleted` 成功路径从 `SCORED` 原子到 `ANALYSIS_READY` 后，创建唯一 `NOTE_WRITE` Job，并继续到 `NOTE_WRITTEN -> COMPLETE`；不得依赖 `_FakeStages` 专用返回形状。
2. `AnalysisSkipped` 行为不回归；重复运行、恢复或已完成 Job 均不增加 Job、Artifact、有效 Provider 调用或笔记。
3. 缓存恢复真实接入既有 Provider-call 与 raw/structured Artifact：核验 request/provider/model identity、Artifact record 与文件 SHA-256，任一缺失、篡改或不匹配均 fail-closed、零新调用/Job 完成；完全匹配缓存仅调用一次有效 Provider 并能安排唯一 NOTE_WRITE。
4. 原 TASK-010 的高/低价值、无字幕、延后直播、不可用、重试/租约/终态、失败隔离和 at-most-once 边界均未被回归。

所有 I/O 只能发生在 pytest 临时目录；严禁真实 Vault、用户笔记、测试目录外写入、网络、云端、凭据、媒体或模型。将 checks、探针、验收矩阵、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT` 追加到 source handoff 并单独提交；不得改状态、merge、push 或清理。
