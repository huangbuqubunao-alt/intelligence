# TASK-005 第三次审查拒绝与 Correction 3 同步 — Status Integrator

你是 Codex Status Integrator，只负责校验并提交主控准备的第三次 Reviewer REJECT、
3 个 P1 和 Correction 3 授权控制面。不得修改准备内容、产品 source 或 handoff，
不得运行 uv、测试、构建、数据库、网络或真实路径，不得启动 Implementer/Reviewer、
合并、push 或清理。

## 固定基线

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main branch/base：`main@2c8492b54e045547b7b3bad742419d8f6fdf0089`
- Git identity：`Mozhu <huangbuqubunao@gmail.com>`
- `user.useConfigOnly=true`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Correction 2：`f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f`
- Third review evidence / source HEAD：
  `30c665181db77607648aa1a6fdbb1d5502b71d7d`
- Review evidence parent：`f95bdb1b5ac0fcdc8906b2daa7138f2f6d60138f`

任一 main/source 基线、身份、父链、分支、洁净度或证据范围不符，立即报告
`BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、
清理或选择其他 SHA。

## 唯一允许提交的 5 个 Markdown 文件

- `agent-prompts/TASK-005-THIRD-REVIEW-REJECT-CORRECTION-3-INTEGRATOR.md`
- `agent-prompts/TASK-005-CORRECTION-3-CODEX.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

初始 `git status --short` 必须精确为 5 个文件，暂存区为空；不得有其他 tracked、
untracked 或 staged 内容。准备文件 hash 在检查前后必须保持一致。

## 只读门禁

1. third review evidence 唯一父提交为 Correction 2，且只修改
   `handoffs/TASK-005.md`；source worktree 干净。
2. handoff Verdict=`REJECT`，P0=0、P1=3、P2=1、P3=0；规定离线命令
   50/30/68、全量 234、两项 mypy、Ruff、CLI、offline build、包内容和 Diff 均
   PASS。拒绝来自 Q1/Q3/Q5 独立反例，不是范围、依赖、许可证、行数或测试数量。
3. 三个 P1 精确为：
   - 公共 SubtitleAdapter 的敏感 message 和错误 stage/video 可穿透 Service 边界；
   - raw source type/actual language 与 canonical rolling quality token 可被自洽
     篡改后命中并推进；
   - 500,000 name runs 全量复制后才拒绝，200,000 空 language buckets 绕过
     512-track 限制；原 P2-2 已升级为 P1。
4. Q2 pre-enumeration reservation/CAS/终态/lease/2 秒恢复和 Q4 VTT/HTTP/安全
   回归已独立 PASS；Correction 3 不得回退或无关重写这些路径。
5. 控制面统一把 TASK-005 退回 `IN_PROGRESS`；第三次 Reviewer 已结束，原 Codex
   Implementer 等待 Correction 3。不得写为 BLOCKED、IN_REVIEW、ACCEPTED 或 DONE。
6. Correction 3 从 `30c6651...` 开始，不 amend/rebase；只允许
   `transcripts.py`、`providers/subtitles.py`、policy/integration tests、
   subtitle fixtures 和 handoff。
7. Correction 包要求：
   - Service 对所有公开 Adapter 错误只保留 code/retryable/retry-after，并重建当前
     video/TRANSCRIPT/safe message；
   - cache provenance 绑定可信 Provider-call response key/确定性 Artifact key，
     而非只验证 token/path 自洽；
   - name runs 和 language buckets 使用已有 1,000/512 边界流式提前拒绝。
8. 不得修改 `state.py`、domain、Schema、migration、`complete_stage`、依赖/锁或
   main。若现有字段无法实现可信 provenance，Implementer 必须按 T-13 报
   `DECISION NEEDED`，不得自行加 Schema。
9. Service 职责/私有 hook 聚合继续登记为 P2；不得预写关闭，也不得仅因该 P2 自动
   拒绝。
10. ADR-007 仍为 `Proposed`；TASK-006/TASK-007 仍为
    `BLOCKED/UNASSIGNED`，TASK-005A 不存在。
11. 真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体、
    真实 Vault/密钥继续未授权。
12. 本轮不运行产品命令，不修改 source，不启动 Worker，不生成下一 Reviewer 包，
    不预写修复成功或审查结论。

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
docs: return TASK-005 for third correction
```

提交后确认：

- 新提交唯一父提交为 `2c8492b54e045547b7b3bad742419d8f6fdf0089`；
- 提交范围精确为 5 个指定 Markdown 文件；
- main/source 均干净，source HEAD 仍为 `30c6651...`；
- 新提交可由
  `git log -1 -- agent-prompts/TASK-005-CORRECTION-3-CODEX.md`
  动态解析为 correction authorization；
- TASK-005=`IN_PROGRESS`，第三次 Reviewer=`REJECT`，Correction 3 尚未启动；
- ADR-007/TASK-006/007 状态未变；
- 未运行产品命令、修改 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-005 third review reject / Correction 3 sync
Role: Status Integrator
Base: main@2c8492b54e045547b7b3bad742419d8f6fdf0089
Head commit:
Git identity:
Committed files:
Checks:
Review evidence/findings:
TASK-005 source/status/roles:
Correction authorization:
ADR-007 and TASK-006/007 status:
Post-commit main/source status:
Verdict: INTEGRATED | BLOCKED
Remaining risks:
```
