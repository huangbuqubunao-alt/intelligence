# TASK-005 Correction 2 实现证据与第三次审查授权同步 — Status Integrator

你是 Codex Status Integrator，只负责校验并提交主控准备的 Correction 2 实现证据、
TASK-005 `IN_REVIEW` 状态和第三次独立 Codex Reviewer 授权。不得修改准备内容、
产品 source 或 handoff，不得运行 uv、测试、构建、数据库、网络或真实路径，不得
启动 Reviewer、合并、push 或清理。

## 固定基线

- Main repository：`/Users/developer/Documents/youtubek agent`
- Main branch/base：`main@e4ab5638d599a5688f75d8e0da03e4a15950da3e`
- Git identity：`Mozhu <maintainer@example.invalid>`
- `user.useConfigOnly=true`
- Source worktree：`/Users/developer/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Second review evidence：`5bb750e8d2f1336b321dbca64e7c409f66853b0f`
- Correction 2 / source HEAD：
  `f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f`
- Correction 2 parent：`5bb750e8d2f1336b321dbca64e7c409f66853b0f`

任一 main/source 基线、身份、父链、分支、洁净度或范围不符，立即报告 `BLOCKED`。
不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、清理或选择其他
SHA。

## 唯一允许提交的 5 个 Markdown 文件

- `agent-prompts/TASK-005-CORRECTION-2-REVIEW-AUTHORIZATION-INTEGRATOR.md`
- `agent-prompts/TASK-005-REVIEWER-3-CODEX.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

初始 `git status --short` 必须精确为 5 个文件，暂存区为空；不得有其他 tracked、
untracked 或 staged 内容。准备文件 hash 在检查前后必须保持一致。

## 只读门禁

1. Correction 2 唯一父提交为 second review evidence，非 merge/amend/rebase；
   source worktree 干净。
2. Correction 2 Diff 精确为：
   - `handoffs/TASK-005.md`
   - `src/youtube_intel/providers/subtitles.py`
   - `src/youtube_intel/transcripts.py`
   - `tests/integration/test_subtitle_provider.py`
   - `tests/unit/test_subtitle_policy.py`
3. 完整 `b28f52d...f95bdb1...` 产品范围仍精确属于原批准的 8 个路径组/11 个文件；
   `domain.py`、contracts test、`state.py`、migration、`complete_stage`、
   `pyproject.toml` 和 `uv.lock` 未被 Correction 2 修改。
4. handoff 记录 Reviewer 2 反例先 RED `11 failed` 后 GREEN；Implementer 自报
   contracts 50、policy 30、integration 68、全量 234、两项 mypy、Ruff、CLI、
   offline build、包内容与固定 Diff 均 PASS。此处只记录自报，不得写成 Reviewer
   APPROVE。
5. 三个 P1 的静态修复证据完整：
   - Adapter/cache/Service 安全异常在活动 `except` 外重抛，结构化复制错误字段；
   - stable raw request reservation 在任何目录枚举前取得，终态重放、失败释放和
     两个真实 SQLite Service 竞态有回归；
   - raw/canonical token、language、provider/model、producer/version、quality、
     path/SHA/symlink provenance 有 fail-closed 回归。
6. 两个 P2 仍明确保留：职责/私有 hook 聚合与嵌套 metadata 资源放大；不得预写为
   已关闭，也不得仅因 P2 自动拒绝。
7. 控制面统一把 TASK-005 设为 `IN_REVIEW`；Correction 2 source 固定为
   `f95bdb1...`，全新第三个独立 Codex Reviewer 已授权但尚未启动。不得写为
   ACCEPTED 或 DONE。
8. Reviewer 包要求独立复跑 Q1-Q5、R2/R3 回归、AC-1 至 AC-5、ADR-006 T-01 至
   T-15 和五轴审查；Reviewer 只可修改 source handoff。
9. ADR-007 仍为 `Proposed`；TASK-006/TASK-007 仍为
   `BLOCKED/UNASSIGNED`，TASK-005A 不存在。
10. 真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体、
    真实 Vault/密钥继续未授权。
11. 本轮不运行产品命令，不修改 source，不启动 Reviewer，不预写 Verdict，不
    merge、push 或清理。

## Diff 与提交

运行：

```bash
git diff --check
git diff --name-status
git diff
```

确认 5 文件范围、状态、SHA、Finding、禁令、空白、EOF 与文件 hash。全部通过后精确
暂存 5 文件，并运行：

```bash
git diff --cached --check
git diff --cached --name-status
git diff --cached
git diff --name-only
```

要求 cached scope 精确为 5 文件，`git diff --name-only` 无输出。提交信息：

```text
docs: authorize TASK-005 correction 2 review
```

提交后确认：

- 新提交唯一父提交为 `e4ab5638d599a5688f75d8e0da03e4a15950da3e`；
- 提交范围精确为 5 个指定 Markdown 文件；
- main/source 均干净，source HEAD 仍为 `f95bdb1...`；
- 新提交可由 `git log -1 -- agent-prompts/TASK-005-REVIEWER-3-CODEX.md`
  动态解析为 review authorization；
- TASK-005=`IN_REVIEW`，第三次 Reviewer 尚未启动；
- ADR-007/TASK-006/007 状态未变；
- 未运行产品命令、修改 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-005 Correction 2 review authorization sync
Role: Status Integrator
Base: main@e4ab5638d599a5688f75d8e0da03e4a15950da3e
Head commit:
Git identity:
Committed files:
Checks:
Correction source/scope/status:
Third Reviewer authorization:
ADR-007 and TASK-006/007 status:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
