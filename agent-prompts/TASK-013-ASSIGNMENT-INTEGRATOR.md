# TASK-013 assignment sync — Worktree / Status Integrator

你是全新的 Codex Worktree / Status Integrator。只创建指定 worktree/branch 并提交主控准备的控制面 Markdown；不得运行产品命令、改 source 产品代码、启动 Worker、推送或清理 worktree。

## 固定对象

- Main base：`main@9462b6a162a1e9a738b4073fa5e8b2252101f6af`；HEAD 必须精确匹配，且新提交必须以它为唯一父提交。
- Target worktree：`/Users/developer/Documents/yia-worktrees/task-013`；branch：`codex/task-013-e2e-acceptance`；二者开始时必须不存在。
- TASK-011/TASK-012 已 `DONE`，TASK-013 的依赖满足。TASK-014 保持 `BLOCKED/UNASSIGNED`。
- 产品负责人只批准测试内组合现有服务的离线验收；没有批准生产 CLI/编排、真实 YouTube/频道、真实 Vault/用户笔记、Whisper/Ollama/OpenAI、密钥、付费调用、网络、媒体、ffmpeg 或 launchd。
- source 卡在分配 base 中为 `BLOCKED/UNASSIGNED` 的冻结快照；实时状态只以本 main 控制面和动态 prompt 为准，不得把快照当作冲突或写回 source。

## 唯一允许提交范围

1. `agent-prompts/TASK-013-ASSIGNMENT-INTEGRATOR.md`
2. `agent-prompts/TASK-013-IMPLEMENTER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013-e2e-acceptance.md`

## 冻结实施范围

- `tests/e2e/test_mvp_flow.py`
- `tests/e2e/test_failure_recovery.py`
- `tests/e2e/fixtures/**`
- `docs/ACCEPTANCE_REPORT.md`
- `handoffs/TASK-013.md`

不改任何生产源码、CLI、配置、Schema/migration、依赖、锁文件、测试配置、既有测试或任务状态。只允许 pytest 临时 SQLite、data 与 Vault 目录和现有 Fake/固定夹具；不得接触测试目录外的文件。

## 必须执行

1. 核验 main HEAD、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index，且工作树仅有上述五个主控准备文件；目标路径/分支必须不存在。
2. 创建 worktree：`git worktree add -b codex/task-013-e2e-acceptance /Users/developer/Documents/yia-worktrees/task-013 9462b6a162a1e9a738b4073fa5e8b2252101f6af`；核验 source branch/HEAD/洁净度。
3. 准备文件仅限上述五个控制面路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
4. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、模型、凭据、launchctl 或任何产品文件 I/O 命令。
5. main 将 TASK-013 设为 `IN_PROGRESS`、Assignee=`Codex`，登记全新独立 Codex Reviewer 在 source commit 后启动；TASK-014 保持 `BLOCKED/UNASSIGNED`。
6. 提交信息：`docs: assign TASK-013 offline acceptance worktree`。提交后 main/source 必须干净，并确认 Implementer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-013 assignment sync
Base / Head: <base> -> <head>
Worktree/branch/base: <path> / <branch> / <base>
Committed files: <exact five>
States: TASK-013=IN_PROGRESS/Codex; TASK-014=BLOCKED/UNASSIGNED
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
