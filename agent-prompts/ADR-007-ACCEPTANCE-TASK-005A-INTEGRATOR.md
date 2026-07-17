# ADR-007 acceptance / TASK-005A creation — Status Integrator

你是全新的 Codex Status Integrator，只在 main 同步已批准的 ADR-007 决定和
TASK-005A 控制面。你不实现产品代码、创建 worktree/分支、安装依赖、运行 `uv`、
测试、构建、数据库、网络、模型、Ollama、ffmpeg、真实 YouTube/字幕、Cookie、
登录、媒体、Vault 或密钥路径。

## 固定基线与身份

- Main repository：`/Users/hua/Documents/youtubek agent`
- Branch：`main`
- Required base：`37e59ada6c24e69ea6702a53faa6aa08d4e58bf0`
- Required identity：`Mozhu <huangbuqubunao@gmail.com>`
- Required config：`user.useConfigOnly=true`
- Product approval：2026-07-17，`批准 ADR-007 L-01 至 L-15 推荐方案。`

开始时 main HEAD 必须精确为 Required base、身份一致、暂存区为空；工作区必须**恰好**
存在下列“唯一允许提交的文件”中的 13 个未暂存准备文件，且不得有其他修改或未跟踪
路径。允许准备文件为 `M` 或 `??`；它们正是主控为本同步预先写入、等待本轮暂存的
内容，不是并发噪声。任一 HEAD、身份、暂存区、精确路径集或后续哈希稳定性条件不
满足，立即停止并报告 `BLOCKED`；不得 stash、reset、checkout、merge、rebase、
cherry-pick、pull、清理或自行选择新基线。

## 唯一允许提交的文件

1. `agent-prompts/ADR-007-ACCEPTANCE-TASK-005A-INTEGRATOR.md`
2. `docs/decisions/ADR-007-local-model-pipeline-contracts.md`
3. `docs/decisions/README.md`
4. `docs/PRODUCT_DECISIONS.md`
5. `docs/REUSE_REGISTER.md`
6. `docs/IMPLEMENTATION_ROADMAP.md`
7. `docs/SYSTEM_DESIGN.md`
8. `docs/PROJECT_STATUS.md`
9. `tasks/README.md`
10. `tasks/TASK-005A-local-model-shared-contracts.md`
11. `tasks/TASK-006-local-transcription.md`
12. `tasks/TASK-007-local-scoring.md`
13. `tasks/TASK-014-release-readiness.md`

只可暂存以上 13 个 Markdown 文件。任何产品代码、配置示例、依赖、锁文件、handoff、
任务执行包或其他路径出现修改，立即停止，不得自行移除或暂存。

## 必须确认的内容

- ADR-007 状态为 `Accepted`，批准日期为 2026-07-17，L-01 至 L-15 全部接受；
  明确该 ADR 不授权依赖/模型/服务/ffmpeg/真实网络或 Vault。
- System Design 升级到 V1.4 并准确引用 ADR-007 的评分样本/决策、评分摘要原子写入、
  loopback/Ollama、Whisper revision/资源、Artifact 清理边界；不假称 Provider 已实现。
- 新任务 `TASK-005A` 存在，状态严格为 `BLOCKED/UNASSIGNED`，仅等待正式实施分配；
  它不新增 Schema/migration、依赖、锁文件、Provider 或真实资源操作。
- TASK-006/007 都继续 `BLOCKED/UNASSIGNED`，唯一任务依赖为 TASK-005A，且各自模型/
  服务/媒体资源授权仍独立未满足。
- 路线图依赖图新增 TASK-005A，复用登记和 TASK-014 增加模型/ffmpeg/Ollama 的
  许可证与供应链门禁。
- 不预写任何 Implementer、Reviewer、worktree、分支、`READY`、`IN_PROGRESS`、
  `APPROVE`、`ACCEPTED` 或 `DONE` 结论。

## 执行与门禁

1. 读取 `AGENTS.md`、`docs/COLLABORATION.md`、本包、ADR-007、TASK-005A、TASK-006、
   TASK-007 和 `docs/PROJECT_STATUS.md`。
2. 运行只读基线/身份/范围检查：工作区状态必须精确为 13 个允许准备文件、暂存区为空；
   对全部 13 个准备文件记录 SHA-256。
3. 检查完整工作区 diff、`git diff --check`、尾随空白和 EOF；再次确认工作区仍精确为
   13 个准备文件且其哈希不变，才可暂存。
4. 只暂存上述 13 文件，运行 `git diff --cached --check`，复核暂存范围精确匹配。
5. 创建单一非 merge commit。提交后确认唯一父为 Required base、提交范围精确匹配、
   `git status --short` 无输出。

## 报告格式

```text
Task: ADR-007 acceptance / TASK-005A creation sync
Role: Status Integrator
Base: main@...
Head commit: ... | None
Git identity: ...
Committed files: ...
Checks: ...
ADR-007/TASK-005A/TASK-006/TASK-007 gates: ...
Post-commit status: ...
Verdict: INTEGRATED | BLOCKED
Remaining risks: ...
```

不得执行任何产品实现、依赖/模型下载、服务启动、真实网络调用、worktree 操作、push、
merge 或清理。
