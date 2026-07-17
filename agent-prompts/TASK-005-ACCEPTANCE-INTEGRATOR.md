# TASK-005 第四次审查验收同步 — Status Integrator

你是 Codex Status Integrator，只负责校验并提交第四次独立审查证据、主控验收状态和风险同步。不得修改准备内容、产品 source 或 handoff，不得运行 uv、测试、构建、数据库、网络或真实路径，不得启动 Product Integrator、合并、push 或清理。

## 固定基线

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main branch/base：`main@f571470d80b1d5805b77960591e7549eae86fe48`
- Git identity：`Mozhu <huangbuqubunao@gmail.com>`；`user.useConfigOnly=true`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Correction 3：`abf2acba25f9732a9511ecd54c4b92ef6c0d68e1`
- Fourth review evidence / source HEAD：`d5268ef08b360e932b5dda9d0fb70d71b13587a4`
- Review evidence parent：`abf2acba25f9732a9511ecd54c4b92ef6c0d68e1`

任一 main/source 基线、身份、父链、分支、洁净度、范围或 review verdict 不符，立即报告 `BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、清理或选择其他 SHA。

## 唯一允许提交的 4 个 Markdown 文件

- `agent-prompts/TASK-005-ACCEPTANCE-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

初始 `git status --short` 必须精确为这 4 个文件，暂存区为空；不得有其他 tracked、untracked 或 staged 内容。准备文件 hash 在检查前后必须保持一致。

## 只读门禁

1. Fourth review evidence 唯一父提交为 Correction 3，且只修改 `handoffs/TASK-005.md`；source worktree 干净。
2. Correction 3 Diff 精确为：
   - `handoffs/TASK-005.md`
   - `src/youtube_intel/providers/subtitles.py`
   - `src/youtube_intel/transcripts.py`
   - `tests/integration/test_subtitle_provider.py`
3. 完整 `b28f52d...d5268ef...` 产品范围仍精确属于原批准的 8 个路径组/11 个文件；无 Schema、`state.py`、`complete_stage`、配置、CLI、依赖或锁文件变更。
4. Fourth Reviewer verdict 为 `APPROVE`：独立复跑 lock/sync、focused 50/30/77、全量 243、mypy/wiring、Ruff、CLI、offline build、包内容与 Diff 均通过；P1 probe A 公共 Adapter 边界、B 可信 provenance、C streaming bounds，以及 Q2/Q4、AC-1 至 AC-5、ADR-006 T-01 至 T-15 全部 PASS。
5. Finding 严格为 P0=0、P1=0、P2=1、P3=0；唯一 P2 是 Service 职责聚合/私有 test hook，非阻断且必须保留为风险，不能写为已关闭。
6. 控制面统一把 TASK-005 设为 `ACCEPTED`，记录 source=`d5268ef...` 与 review evidence；不得写为 DONE，也不得预写 merge SHA 或 Integrator 结果。
7. ADR-007 仍为 `Proposed`；TASK-005A 不存在；TASK-006/TASK-007 仍为 `BLOCKED/UNASSIGNED`。
8. 真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体、真实 Vault/密钥继续未授权。
9. 本轮不运行产品命令，不修改 source，不启动 Worker，不 merge、push 或清理。

## Diff 与提交

运行：

```bash
git diff --check
git diff --name-status
git diff
```

确认 4 文件范围、状态、SHA、Verdict、P2、禁令、空白、EOF 与文件 hash。全部通过后精确暂存 4 文件，并运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
```

要求 cached scope 精确为 4 文件，`git diff --name-only` 无输出。提交信息：

```text
docs: accept TASK-005 correction 3
```

提交后确认：

- 新提交唯一父提交为 `f571470d80b1d5805b77960591e7549eae86fe48`；
- 提交范围精确为 4 个指定 Markdown 文件；
- main/source 均干净，source HEAD 仍为 `d5268ef...`；
- TASK-005=`ACCEPTED`，尚未合并、尚未关闭为 DONE，Product Integrator 尚未启动；
- ADR-007/TASK-006/007 状态未变；
- 未运行产品命令、修改 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-005 acceptance sync
Role: Status Integrator
Base: main@f571470d80b1d5805b77960591e7549eae86fe48
Head commit:
Git identity:
Committed files:
Checks:
Review/source/status:
P2 risk:
ADR-007 and TASK-006/007 status:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
