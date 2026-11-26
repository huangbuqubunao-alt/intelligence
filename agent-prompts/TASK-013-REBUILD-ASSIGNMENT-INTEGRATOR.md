# TASK-013 rebuild assignment sync — Worktree / Status Integrator

你是全新的 Codex Worktree / Status Integrator。只创建获批 worktree/branch 并提交主控准备的控制面 Markdown；不得运行产品命令、修改 source、启动 Implementer/Reviewer、合并、推送或清理。

## 固定对象

- Main base：`main@2a59dfe3860161a5989f2c08161f03c73aa4ca86`，必须干净且为唯一父基线。
- 新目标 worktree：`/Users/developer/Documents/yia-worktrees/task-013-rebuild`；新分支：`codex/task-013-e2e-acceptance-rebuild`。两者开始时必须不存在。
- 历史 worktree `/Users/developer/Documents/yia-worktrees/task-013` / `codex/task-013-e2e-acceptance@2afd95a...` 是已拒绝证据，必须保留且不得访问、修改、清理或复用。
- TASK-013A 已为 `DONE`；产品负责人已批准 TASK-013 在全新 worktree 中重建离线验收，Codex 是唯一 Implementer，完成后由全新独立 Codex Reviewer 审查。

## source 唯一允许路径组

1. `tests/e2e/test_mvp_flow.py`
2. `tests/e2e/test_failure_recovery.py`
3. `tests/e2e/fixtures/**`
4. `docs/ACCEPTANCE_REPORT.md`
5. `handoffs/TASK-013.md`

只允许测试内组合既有生产服务、Fake 外部 Adapter 和 pytest 临时 SQLite/DATA/Vault。不得修改生产代码、CLI/编排、配置、Schema/migration、依赖/锁、测试配置、既有测试或 TASK-013A。不得调用真实模型、ffmpeg、媒体/YouTube、网络、OpenAI/Ollama、真实 Vault/用户笔记、凭据或付费服务。

## 唯一允许提交范围

1. `agent-prompts/TASK-013-REBUILD-ASSIGNMENT-INTEGRATOR.md`
2. `agent-prompts/TASK-013-REBUILD-IMPLEMENTER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013-e2e-acceptance.md`

## 必须执行

1. 核验 main identity `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、分支/HEAD、empty index/worktree、目标路径/分支不存在及精确五文件范围。
2. 从固定 base 创建新 branch/worktree，核验 branch、HEAD 和洁净度。source 内 `BLOCKED/UNASSIGNED` 是固定 base 快照；实时控制面只在 main。
3. 对准备文件做两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围核验；字节漂移立即停止。
4. main 将 TASK-013 设为 `IN_PROGRESS/Codex`，记录新 worktree、分支、base、五路径范围及离线资源边界；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-014 继续 BLOCKED。
5. 提交信息：`docs: assign TASK-013 real-flow acceptance rebuild`。提交后 main/new source 必须干净，确认 Implementer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-013 rebuild assignment sync
Base / Head: <base> -> <head>
Worktree/branch/base: <path> / <branch> / <base>
Committed files: <exact five>
States: TASK-013=IN_PROGRESS/Codex; TASK-014=BLOCKED/UNASSIGNED
Checks: <Git-only/worktree gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
