# TASK-010 收口 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的 TASK-010 收口控制面 Markdown；不得运行产品命令、改 source、再次合并、推送或清理 worktree。

## 固定对象

- Main base：`main@722b485e4c4f57c6f1689dff69e908e8ec52f0f2`，必须干净且为唯一父基线。
- Integrating merge：`3d2122c8720e9bfcb7c61088beb2955ffe6f1658`，父提交顺序必须精确为 execution base `8e8b775e7c294f44f410c6b53d0a089e86756aef` 与 accepted source `e12af35b903705d782538617469da0c8a71671e9`。
- Retained source：`/Users/hua/Documents/yia-worktrees/task-010` / `codex/task-010-orchestration-recovery@e12af35b903705d782538617469da0c8a71671e9`，必须干净且 source 为 main 祖先。
- Merge first-parent Diff 必须精确为六个 TASK-010 批准路径：`jobs.py`、`pipeline.py`、`retry.py`、`test_pipeline.py`、`test_recovery.py`、`handoffs/TASK-010.md`。
- TASK-008/TASK-009 均已 `DONE`，不得读取、修改、清理或等待其 source worktree。

## 已有整合证据

- Accepted Reviewer 2 evidence `e12af35...` 为 `APPROVE`，P0–P3=0。
- Product Integrator 的 merge `3d2122c...` 已重跑 lock/sync、TASK-010 integration=`17`、full pytest=`399`、mypy、Ruff、CLI、offline build、sdist/wheel migration/template inclusion、Diff 与凭据模式扫描，均通过。
- 真实网络、OpenAI/模型、媒体、凭据和真实 Vault 继续未运行且未授权；外部调用成功但 DB 提交前中断只保留既有 at-most-once best-effort 风险。

## 唯一允许提交范围

1. `agent-prompts/TASK-010-CLOSURE-INTEGRATOR.md`
2. `docs/PROJECT_STATUS.md`
3. `handoffs/TASK-010.md`
4. `tasks/README.md`
5. `tasks/TASK-010-orchestration-recovery.md`

不得暂存任何产品代码、依赖、锁、Schema、迁移或 source 文件。

## 必须执行

1. 核验 main/source branch、HEAD、merge 双父、source ancestor、first-parent 六路径范围、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、empty index/worktree。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不重跑 uv、pytest、build、数据库、网络、Vault、云端、凭据或任何产品命令；只记录已有整合证据。
4. 使 TASK-010 card/index/project status/handoff 一致为 `DONE`，记录 merge SHA；不得改变已整合的产品范围或下游状态。
5. 提交信息：`docs: close TASK-010 after integration`。提交后 main/source 必须干净；不 push、不清理 worktree。

## 回传格式

```text
Task: TASK-010 closure
Base / Head: <base> -> <head>
Merge/source/status: <merge> / <source> / TASK-010=DONE
Committed files: <exact five>
Checks: <Git-only closure gates>
Product commands: not rerun by package
Verdict: INTEGRATED | BLOCKED
Remaining risks: <retained risks>
```
