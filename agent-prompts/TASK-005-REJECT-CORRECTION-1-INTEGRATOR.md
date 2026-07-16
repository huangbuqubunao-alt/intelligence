# TASK-005 第一次审查拒绝与 Correction 1 同步 — Status Integrator

你是 Codex Status Integrator，只负责校验并提交主控准备的 Reviewer REJECT、5 个 P1
和 Correction 1 授权控制面。不得修改准备内容、产品 source 或 handoff，不得运行
uv、测试、构建、数据库、网络或真实路径，不得启动 Implementer/Reviewer、合并、
push 或清理。

## 固定基线

- Main repository：`/Users/hua/Documents/youtubek agent`
- Main branch/base：`main@095380b7263aa3d04c7d133c1e17d8f4f2fea082`
- Git identity：`Mozhu <huangbuqubunao@gmail.com>`
- `user.useConfigOnly=true`
- Source worktree：`/Users/hua/Documents/yia-worktrees/task-005`
- Source branch：`codex/task-005-subtitle-pipeline`
- Implementation：`98d19700818bcae14efc412aaaaeb6eed97a1535`
- Review evidence / source HEAD：
  `515c34894bb138115a4658d962fb5ef0aa7d9d80`
- Review evidence parent：`98d19700818bcae14efc412aaaaeb6eed97a1535`

任一 main/source 基线、身份、父链、分支、洁净度或证据范围不符，立即报告
`BLOCKED`。不得 stash、reset、checkout、merge、rebase、cherry-pick、pull、
清理或选择其他 SHA。

## 唯一允许提交的 5 个 Markdown 文件

- `agent-prompts/TASK-005-REJECT-CORRECTION-1-INTEGRATOR.md`
- `agent-prompts/TASK-005-CORRECTION-1-CODEX.md`
- `docs/PROJECT_STATUS.md`
- `tasks/README.md`
- `tasks/TASK-005-subtitle-pipeline.md`

初始 `git status --short` 必须精确为 5 个文件，暂存区为空；不得有其他 tracked、
untracked 或 staged 内容。准备文件 hash 在检查前后必须保持一致。

## 只读门禁

1. review evidence 唯一父提交为 implementation，且只修改
   `handoffs/TASK-005.md`；source worktree 干净。
2. handoff Verdict=`REJECT`，P0=0、P1=5、P2=1、P3=0；规定离线命令最终均有 PASS
   证据，拒绝原因来自独立反例，不是范围、依赖、许可证或行数自动触发。
3. 五个 P1 精确为：异常链泄漏正文、VTT speaker/cue 语义丢失、Adapter 短读/格式/
   payload 边界不完整、Provider-call 幂等/恢复错误、canonical-only 失效不能从
   verified raw 重建。
4. 控制面统一把 TASK-005 退回 `IN_PROGRESS`；Reviewer 已结束，原 Codex
   Implementer 等待 Correction 1。不得写为 BLOCKED、IN_REVIEW、ACCEPTED 或 DONE。
5. Correction 包从 `515c348...` 开始，不 amend/rebase；只允许
   `transcripts.py`、`providers/subtitles.py`、policy/integration tests、
   subtitle fixtures 和 handoff。
6. Correction 包逐项包含 Reviewer 的复现、冻结 payload 长度、现有
   `fail_provider_call` 释放租约、既有 Provider-call 预检、all-invalid 稳定结果和
   verified raw→canonical 重建；不得修改 `state.py`、domain、Schema、依赖/锁或
   main。
7. P2 只要求在修复 P1 时提取具名私有 helper、避免继续扩大 `fetch`；不得扩成无关
   大重构或新增产品模块。
8. ADR-007 仍为 `Proposed`；TASK-006/TASK-007 仍为
   `BLOCKED/UNASSIGNED`，TASK-005A 不存在。
9. 真实 YouTube/字幕、Cookie/登录/`.netrc`、remote components、ffmpeg、媒体、
   真实 Vault/密钥继续未授权。
10. 本轮不运行产品命令，不修改 source，不启动 Worker，不预写修复成功或 Reviewer
    结论。

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
docs: return TASK-005 for subtitle correction
```

提交后确认：

- 新提交唯一父提交为 `095380b7263aa3d04c7d133c1e17d8f4f2fea082`；
- 提交范围精确为 5 个指定 Markdown 文件；
- main/source 均干净，source HEAD 仍为 `515c348...`；
- 新提交可由 `git log -1 -- agent-prompts/TASK-005-CORRECTION-1-CODEX.md`
  动态解析为 correction authorization；
- TASK-005=`IN_PROGRESS`，Reviewer=`REJECT`，Correction 1 尚未启动；
- ADR-007/TASK-006/007 状态未变；
- 未运行产品命令、修改 source、启动 Worker、merge、push 或清理。

## 回传格式

```text
Task: TASK-005 first review reject / Correction 1 sync
Role: Status Integrator
Base: main@095380b7263aa3d04c7d133c1e17d8f4f2fea082
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
