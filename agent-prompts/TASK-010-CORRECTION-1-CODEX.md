# TASK-010 Correction 1 — Codex Implementer

你是原 TASK-010 Codex Implementer。只修复独立审查发现的高价值分析成功后未排程 NOTE_WRITE 的 P1；不得重构、合并、推送、修改 main 或任务状态，也不得接触真实资源。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-010-CORRECTION-1-CODEX.md` 必须解析为本 Correction 1 控制面提交，且 main 中 TASK-010=`IN_PROGRESS`。
- Worktree/branch：`/Users/developer/Documents/yia-worktrees/task-010` / `codex/task-010-orchestration-recovery`。
- 起始 source HEAD：`f929a2f114626f7f714134d0894b188548537e4e`，唯一父为 implementation `e17d732db4cfb344ddd75ac8bc25990c216afc3f`；worktree 必须干净，不能有 `.codebase-memory/` 或其他工件。
- 分配前 base：`227bdeba3a4d9ddd57231b123bfdc4a2038af3d3`。source 任务卡/项目状态的旧快照不是可写控制面。

## 唯一允许修改

- `src/youtube_intel/pipeline.py`
- `tests/integration/test_pipeline.py`
- `tests/integration/test_recovery.py`
- `handoffs/TASK-010.md`

禁止 jobs/retry 以外的生产改动、领域/配置、`state.py`、Schema/migration、Provider、CLI、依赖/锁文件、TASK-008/TASK-009 或 main 变更。若该范围不足，停止并报告 `DECISION NEEDED`。

## P1 与完成标准

`RepositoryBackedAnalysisService.analyze()` 成功返回 `AnalysisCompleted` 后，编排层必须把既有 `SCORED -> ANALYSIS_READY` 的原子完成结果视为可继续排程，确保创建唯一的 `NOTE_WRITE` Job 并最终可到 `NOTE_WRITTEN -> COMPLETE`；`AnalysisSkipped` 的既有语义不得回归。

不得改变 `complete_stage`、Provider、Schema 或公共契约。不得以 `_FakeStages` 的专用返回值掩盖真实服务返回形状；必须使用临时 SQLite 和真实 repository-backed 分析服务适配边界回归。重复运行/恢复不得重复有效 Provider 调用、Artifact、Job 或笔记。同步补足 Reviewer 指出的 P2：缓存恢复的测试必须接入既有 Provider-call/Artifact 身份与哈希验证，而不能只依赖内存 `_cached_calls` 计数。

## 强制验证

运行 lock check、locked sync、两份 TASK-010 集成测试、全量 pytest、mypy、Ruff、CLI help、offline build、sdist/wheel migration/template inclusion 与 `git diff --check 227bdeba3a4d9ddd57231b123bfdc4a2038af3d3...HEAD`。审查完整 diff；记录实际复用、真实资源未运行与 at-most-once 剩余边界。

所有 I/O 只能发生在 pytest 创建的临时 SQLite/文件目录。严禁真实 Vault、用户笔记、测试目录外写入/删除/移动、真实网络、云端、凭据、媒体或模型路径。

完成后追加 source handoff，创建一个单父提交，父提交严格为 `f929a2f...`，并回报 SHA、范围、检查与剩余风险；不得启动 Reviewer 或修改状态。
