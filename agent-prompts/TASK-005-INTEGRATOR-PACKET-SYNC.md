# TASK-005 Product Integrator 开工包同步 — Status Integrator

你是 Codex Status Integrator，只负责校验并提交主控准备的 TASK-005 Product Integrator 开工包和状态同步。不得修改准备内容、产品 source 或 handoff，不得运行 uv、测试、构建、数据库、网络或真实路径，不得启动 Product Integrator、合并、push 或清理。

## 固定基线

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main branch/base：`main@7ed6a3ea096e05a1861a4e56c1c9207ef5aaebd0`
- Git identity：`Mozhu <maintainer@example.invalid>`；`user.useConfigOnly=true`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Accepted source / fourth review evidence：`d5268ef08b360e932b5dda9d0fb70d71b13587a4`
- Review evidence parent：`abf2acba25f9732a9511ecd54c4b92ef6c0d68e1`

任一 main/source 基线、身份、父链、分支、洁净度、ACCEPTED 状态、范围或 review verdict 不符，立即报告 `BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、清理或选择其他 SHA。

## 唯一允许提交的 5 个 Markdown 文件

- `agent-prompts/TASK-005-INTEGRATOR-PACKET-SYNC.md`
- `agent-prompts/TASK-005-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

初始 `git status --short` 必须精确为这 5 个文件，暂存区为空；不得有其他 tracked、untracked 或 staged 内容。准备文件 hash 在检查前后必须保持一致。

## 只读门禁

1. TASK-005=`ACCEPTED`，fourth Reviewer verdict=`APPROVE`，P0/P1=0；唯一 P2 是 Service 职责/私有 test hook 聚合，非阻断且必须保留。
2. Fourth review evidence 唯一父提交为 Correction 3，且只修改 `handoffs/TASK-005.md`；source worktree 干净。
3. Correction 3 Diff 精确为 4 文件：handoff、`transcripts.py`、`providers/subtitles.py`、integration tests；完整 `b28f52d...d5268ef...` 产品范围仍只属于原批准的 8 个路径组/11 个文件。
4. 受影响离线门禁证据完整：lock/sync、focused 50/30/77、全量 243、mypy/wiring、Ruff、CLI、offline build、包内容、Diff，以及 P1 A/B/C、Q2/Q4、AC-1 至 AC-5、ADR-006 T-01 至 T-15 均 PASS。
5. Integrator 包固定 source `d5268ef...`，要求无冲突的 `--no-ff --no-commit` merge、重跑受影响门禁、验证 first-parent 11 文件范围和 migration/module 打包；不得开发、重审、扩大范围、修改任务状态或清理 source 分支/worktree。
6. TASK-005 保持 `ACCEPTED`，不得预写 merge SHA 或 DONE；Product Integrator 尚未启动。
7. ADR-007=`Proposed`；TASK-005A 不存在；TASK-006/TASK-007 仍为 `BLOCKED/UNASSIGNED`。
8. 真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体、真实 Vault/密钥继续未授权。
9. 本轮不运行产品命令，不修改 source，不启动 Worker，不 merge、push 或清理。

## Diff 与提交

运行：

```bash
git diff --check
git diff --name-status
git diff
```

确认 5 文件范围、状态、SHA、P2、禁令、空白、EOF 与文件 hash。全部通过后精确暂存 5 文件，并运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
```

要求 cached scope 精确为 5 文件，`git diff --name-only` 无输出。提交信息：

```text
docs: authorize TASK-005 integration
```

提交后确认：

- 新提交唯一父提交为 `7ed6a3ea096e05a1861a4e56c1c9207ef5aaebd0`；
- 提交范围精确为 5 个指定 Markdown 文件；
- main/source 均干净，source HEAD 仍为 `d5268ef...`；
- 新提交可由 `git log -1 -- agent-prompts/TASK-005-INTEGRATOR.md` 动态解析为 Product Integrator execution base；
- TASK-005=`ACCEPTED`，尚未合并或关闭为 DONE；
- ADR-007/TASK-006/007 状态未变；
- 未运行产品命令、修改 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-005 integrator-packet sync
Role: Status Integrator
Base: main@7ed6a3ea096e05a1861a4e56c1c9207ef5aaebd0
Head commit:
Git identity:
Committed files:
Checks:
Review/source/status:
P2 risk:
Integrator authorization:
ADR-007 and TASK-006/007 status:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
