# TASK-005 整合后关闭同步 — Status Integrator

你是 Codex Status Integrator，只负责校验并提交 TASK-005 的主控验收、整合结果和最终 `DONE` 状态。不得修改产品 source、测试、依赖、锁文件或 source worktree，不得运行 uv、测试、构建、数据库、网络或真实路径，不得创建 TASK-005A、启动 TASK-006/007、push 或清理。

## 固定基线

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main branch/base：`main@cfc302ddc41cd908777f49de292327640b6f8314`
- Git identity：`Mozhu <huangbuqubunao@gmail.com>`；`user.useConfigOnly=true`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Accepted source/review evidence：`d5268ef08b360e932b5dda9d0fb70d71b13587a4`
- Merge commit：`cfc302ddc41cd908777f49de292327640b6f8314`
- Merge parents：`1e5e5f8ade1a9566e6ee32b6d720cbcc94f03bc8`、`d5268ef08b360e932b5dda9d0fb70d71b13587a4`

任一 main/source 基线、身份、双父链、分支、洁净度、first-parent 范围、ACCEPTED 状态或整合后检查不符，立即报告 `BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、清理或选择其他 SHA。

## 唯一允许提交的 5 个 Markdown 文件

- `agent-prompts/TASK-005-CLOSURE-INTEGRATOR.md`
- `docs/PROJECT_STATUS.md`
- `handoffs/TASK-005.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

初始 `git status --short` 必须精确为这 5 个文件，暂存区为空；不得有其他 tracked、untracked 或 staged 内容。准备文件 hash 在检查前后必须保持一致。

## 只读门禁

1. Merge commit 是双父提交，第一父为 `1e5e5f8...`、第二父为 accepted source `d5268ef...`；source evidence 是 merge 祖先。
2. `git diff cfc302...^1 cfc302... --name-only` 精确为 11 个已批准 TASK-005 文件；`pyproject.toml` 与 `uv.lock` 未变。
3. Product Integrator 已独立重跑 lock/sync、focused 50/30/77、全量 243、mypy/wiring、Ruff、CLI、offline build 与 package inclusion，全部 PASS；没有 unexpected files、push 或 source cleanup。
4. Fourth Reviewer evidence 为 `APPROVE`，P0/P1=0；唯一 P2 是 Service 职责/私有 test hook 聚合，非阻断但必须保留。
5. 在 `handoffs/TASK-005.md` 只补全末尾的主控验收与整合结果：`Orchestrator: Codex`、`Verdict: ACCEPT`、批准整合 commit、Integrator、merge SHA、整合后检查和最终状态 `DONE`。不得改写历史 Implementer/Reviewer 证据。
6. 控制面统一把 TASK-005 设为 `DONE`，记录 merge `cfc302...`；TASK-006/TASK-007 仍为 `BLOCKED/UNASSIGNED`，因为 ADR-007 仍是 `Proposed` 且 TASK-005A 不存在。
7. 保留 P2、真实 YouTube/认证/媒体/Vault 未授权、上游 payload 漂移与 mutagen 许可证门禁风险；不得写为已解决。
8. 本轮不运行产品命令、不修改 source/任务实现、不启动 Worker、merge、push 或清理。

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
docs: close TASK-005 subtitle pipeline
```

提交后确认：

- 新提交唯一父提交为 `cfc302ddc41cd908777f49de292327640b6f8314`；
- 提交范围精确为 5 个指定 Markdown 文件；
- main/source 均干净，source HEAD 仍为 `d5268ef...` 且保留；
- TASK-005=`DONE`，merge `cfc302...` 已记录；
- ADR-007/TASK-006/007 状态未变；
- 未运行产品命令、修改 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-005 closure
Role: Status Integrator
Base: main@cfc302ddc41cd908777f49de292327640b6f8314
Head commit:
Git identity:
Committed files:
Checks:
Merge/source/status:
P2 and release risks:
ADR-007 and TASK-006/007 status:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
