# TASK-010 — 第一位独立 Codex Reviewer

你是全新独立 Codex Reviewer。只审查 TASK-010 source，不修业务代码；唯一可写文件为 source `handoffs/TASK-010.md`。任何 P0/P1、范围异常、未授权资源路径或 source 不干净均立即 `REJECT` 并停止。

## 固定对象

- Main authorization：动态读取 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-010-REVIEWER-CODEX.md`；main 中 TASK-010 必须为 `IN_REVIEW`。
- Source/base：`/Users/hua/Documents/yia-worktrees/task-010` /
  `codex/task-010-orchestration-recovery@e17d732db4cfb344ddd75ac8bc25990c216afc3f` /
  `227bdeba3a4d9ddd57231b123bfdc4a2038af3d3`。
- Implementation 唯一父为 fixed base；完整允许范围严格为 `pipeline.py`、`jobs.py`、`retry.py`、
  `test_pipeline.py`、`test_recovery.py` 与 source handoff。
- Source 任务卡和项目状态是分配时快照；不得作为冲突或写回 source。不得读取、修改或清理 TASK-008/TASK-009 source。

## 洁净度与索引门禁

开始时 `git status --short --untracked-files=all` 必须无输出。不得在 TASK-010 source 运行会写入 `.codebase-memory/` 的索引动作；优先使用已配置的 codebase-memory MCP（必要时再用 CodeGraph）做窄范围只读定位。任何范围外工件都必须 `REJECT`，不自行清理。

## 强制审查

1. 核验 main/source HEAD、父链、完整 Diff 和范围；禁止领域/配置、`state.py`、Schema/migration、Provider、CLI、依赖/锁或 TASK-008/TASK-009 改动。
2. 独立复跑：lock check、locked sync、两份 TASK-010 集成测试、全量 pytest、mypy、Ruff、CLI help、offline build、sdist/wheel migration/template inclusion 与固定 `git diff --check`。
3. 在 pytest 临时 SQLite/Fake 中独立验证：
   - 高价值、低价值、无字幕、延后直播、不可用内容路径和非法 Pipeline/Job 转换；
   - 每个昂贵阶段调用前、调用后但落库前、落库后中断后的租约回收、缓存恢复、状态/Artifact/Job 语义；
   - 重试次数与退避、`FAILED_FINAL`、单视频失败隔离、重复批次零新增 Job/Artifact/有效调用/笔记；
   - 不捕获全部异常伪装成功，最近成功 `PipelineStatus` 不被失败尝试覆盖。
4. 核对 `complete_stage`、Provider-call/Artifact 缓存和既有 State Repository 契约没有被旁路或重定义；不得因为 Fake 成功就忽略真实边界必须保留的 at-most-once 风险。
5. 在 source handoff 追加 checks、探针、验收矩阵、P0–P3、skipped/risks 与 `APPROVE` 或 `REJECT`；单独提交 handoff。不得改任务状态、merge、push 或清理。

所有 I/O 只能发生在 pytest 创建的临时 SQLite/文件目录。严禁真实 Vault、用户笔记、测试目录外写入/删除/移动、真实网络、云端、凭据、媒体或模型路径。
