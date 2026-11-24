# TASK-012 assignment sync — Worktree / Status Integrator

你是全新的 Codex Worktree / Status Integrator。只创建指定 worktree/branch 并提交主控准备的控制面 Markdown；不得运行产品命令、改 source 产品代码、启动 Worker、推送或清理 worktree。

## 固定对象

- Main base：`main@8e322f362d2ff0972ee987b7c06c8453a9dce73d`，必须干净且为唯一父基线。
- Target worktree：`/Users/developer/Documents/yia-worktrees/task-012`；branch：`codex/task-012-cli-operations`；二者开始时必须不存在。
- TASK-011 已 `DONE`，merge=`2ba42c2f55082f5ce74ddc04d8aa18a7ef85fae1`，因此 ADR-011 O-06 的 `weekly` CLI 上游依赖已满足。
- TASK-012 source 卡在分配 base 中为 `BLOCKED/UNASSIGNED` 的冻结快照；实时状态只以本 main 控制面和动态 prompt 为准，不得把快照当作冲突或写回 source。

## 唯一允许提交范围

1. `agent-prompts/TASK-012-ASSIGNMENT-INTEGRATOR.md`
2. `agent-prompts/TASK-012-IMPLEMENTER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-012-cli-operations.md`

## TASK-012 冻结实现范围

- `src/youtube_intel/__main__.py`
- `src/youtube_intel/cli.py`
- `src/youtube_intel/logging.py`
- `config/launchd/com.yia.agent.daily.plist.example`
- `config/launchd/com.yia.agent.weekly.plist.example`
- `docs/operations.md`
- `tests/integration/test_operations.py`
- `handoffs/TASK-012.md`

不新增依赖或锁文件，不改 Schema/migration、state、domain/config、Provider、模板、launchctl、真实 Vault 或用户内容。只允许任务卡和 ADR-011 的离线验证；launchd 只可 `plutil -lint` 静态样例。

## 必须执行

1. 核验 main HEAD、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、空 index/worktree、目标路径/分支不存在，以及 TASK-011 merge 证据。
2. 创建 worktree：`git worktree add -b codex/task-012-cli-operations /Users/developer/Documents/yia-worktrees/task-012 8e322f362d2ff0972ee987b7c06c8453a9dce73d`；核验 source branch/HEAD/洁净度。
3. 准备文件仅限上述五个控制面路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
4. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据、launchctl、plutil 或任何产品文件 I/O 命令。
5. main 将 TASK-012 设为 `IN_PROGRESS`、Assignee=`Codex`，授权全新独立 Codex Reviewer 在 source commit 后启动；TASK-013/014 保持 `BLOCKED/UNASSIGNED`。
6. 提交信息：`docs: assign TASK-012 worktree`。提交后 main/source 必须干净，并确认 Implementer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-012 assignment sync
Base / Head: <base> -> <head>
Worktree/branch/base: <path> / <branch> / <base>
Committed files: <exact five>
States: TASK-012=IN_PROGRESS/Codex; TASK-013/014=BLOCKED/UNASSIGNED
Checks: <Git-only gates>
Verdict: INTEGRATED | BLOCKED
```
