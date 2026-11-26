# TASK-010 — Codex Implementer

你是 TASK-010 的唯一 Codex Implementer。只在指定 worktree 实施流程编排与恢复；不得合并、push、rebase、修改 main 或任务状态。目标是让既有切片在统一 Pipeline 状态机中可幂等恢复，而不新增 Provider、输出格式或真实资源路径。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-010-IMPLEMENTER-CODEX.md` 必须解析为本分配控制面提交，且 main 中 TASK-010=`IN_PROGRESS`。
- Worktree/branch：`/Users/developer/Documents/yia-worktrees/task-010` / `codex/task-010-orchestration-recovery`。
- 固定 base：`227bdeba3a4d9ddd57231b123bfdc4a2038af3d3`；开始时 worktree 必须干净，无 `.codebase-memory/` 或其他工件。
- 依赖 TASK-003 至 TASK-009 已在 main 关闭为 `DONE`。source 任务卡和项目状态的旧快照不是可写控制面。

## 开工前

按仓库 AGENTS.md 的顺序阅读协作、状态、PRD、系统设计、复用登记、TASK-010 任务卡和本授权包。用已配置的 codebase-memory MCP（必要时再用 CodeGraph）定位现有状态、Job、Artifact、Provider 协议与阶段完成契约；不要用会写入 source 的索引动作。先报告目标、完成标准、依赖、预期修改文件与 Reuse decision。

## 唯一允许修改

- `src/youtube_intel/pipeline.py`
- `src/youtube_intel/jobs.py`
- `src/youtube_intel/retry.py`
- `tests/integration/test_pipeline.py`
- `tests/integration/test_recovery.py`
- `handoffs/TASK-010.md`

若既有代码结构使这六个路径无法满足任务卡验收，停止并报告 `DECISION NEEDED`；不得擅自修改领域/配置、`state.py`、Schema/migration、Provider、CLI、依赖/锁文件或其他测试。

## 实施与复用边界

- `DIRECT`：既有 Domain、State Repository、Provider Protocol、Artifact、Job lease、`complete_stage` 与 Python 标准库；不得重新实现或旁路其语义。
- `REJECT`：新增依赖、ORM、队列、调度器、Provider、真实网络/模型/凭据/Vault、Schema/migration 或输出格式。
- 完成高分、低分、无字幕、延后直播和不可用内容的既定状态路径；在调用前、调用后落库前、落库后注入中断，恢复时不得重复有效缓存调用。
- 复用既有重试、租约、状态和缓存契约；单个视频失败不得阻塞批次，非法转换必须拒绝。不得用捕获所有异常或标记成功掩盖失败。
- 所有 Provider 使用既有 Fake，文件/SQLite I/O 仅限 pytest 临时目录；严禁真实 Vault、用户笔记、网络、云端、凭据、媒体或模型。

## 强制验证

运行任务卡的两组集成测试、全量 pytest、mypy、Ruff、CLI help、lock check、locked sync、offline build、sdist/wheel migration/template inclusion 和 `git diff --check 227bdeba3a4d9ddd57231b123bfdc4a2038af3d3...HEAD`。人工核验同一固定批次连续运行两次后记录数、调用数和笔记数不增加。

完成后审查完整 diff，追加 handoff（含状态路径、故障矩阵、两次运行计数、实际复用、未授权路径和 remaining risks），创建一个单父提交并回报 SHA、范围、检查和风险。不得启动 Reviewer 或修改任务状态。
