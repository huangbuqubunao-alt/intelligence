# TASK-008 Correction 3 审查授权同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@21e2d2b5ed8c87d3f4a499643a5a1d8431ae47ca`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@7a543d0acfe25d1c3d9fd06c4647683ed1487a47`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Correction：`7a543d0...` 唯一父为 reviewer-3 evidence `b380a8c87d99a3d2dbf88b28bde3ec5b0de4da0f`；Correction 仅改 `analysis.py`、`test_summary_provider.py` 与 handoff。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-008 七个批准路径组中的六个实际路径。

## Correction 关闭目标

- Reviewer-3 evidence `b380a8c...` 为 `REJECT`：持久化路径在关闭、低价值和凭据门禁前预留 ProviderCall。
- Correction 自报按 A-03 完整顺序处理上游资格、关闭、token/缓存、预算、凭据、预留；关闭/低价值/缺凭据零副作用，缓存重排零 credential/transport/新 call/artifact 且可按 A-12 复用成功证据原子完成当前 Job。
- 全部是 Implementer 自报，必须由新 Reviewer 独立复跑；不得预写 `APPROVE`、`ACCEPTED`、merge 或 `DONE`。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-CORRECTION-3-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-008-REVIEWER-4-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

不得访问或修改 TASK-009 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、干净 index/worktree、Correction 三路径及完整范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、模型、Vault、凭据或文件删除命令。
4. main 将 TASK-008 标为 `IN_REVIEW`，授权全新独立 Reviewer 4；TASK-009 继续 `IN_PROGRESS` 且未触碰。
5. 提交信息：`docs: authorize TASK-008 policy order review`。提交后 main/source 必须干净，并确认 Reviewer 4 prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-008 Correction 3 review authorization sync
Base / Head: <base> -> <head>
Source/correction/status: <chain>; TASK-008=IN_REVIEW
Committed files: <exact five>
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
```
