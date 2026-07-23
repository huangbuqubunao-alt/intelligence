# ADR-010 / ADR-011 acceptance sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的 ADR 与任务控制面 Markdown；不得创建 worktree/branch、启动 Worker、运行产品命令、修改 source 或访问真实资源。

## 固定对象

- Main base：`main@1a07cc9cf11e08525568b5b0ceb794d425503152`，必须干净且为唯一父基线。
- 产品负责人已明确批准：TASK-011 使用 completed_at 的配置时区 ISO 周、确定性聚合、包内固定模板和仅 pytest 临时 Vault；TASK-012 使用无副作用 doctor、结构化 JSONL、无自动删除以及每日/每周可选的静态 launchd 示例。
- TASK-011 获得后续正式实施所需的范围与资源边界，但本次不创建 worktree。TASK-012 的 `weekly` CLI 依赖 TASK-011，继续 `BLOCKED/UNASSIGNED`。

## 唯一允许提交范围

1. `agent-prompts/ADR-010-011-ACCEPTANCE-INTEGRATOR.md`
2. `docs/PRODUCT_DECISIONS.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/REUSE_REGISTER.md`
5. `docs/SYSTEM_DESIGN.md`
6. `docs/decisions/ADR-010-weekly-report-contract.md`
7. `docs/decisions/ADR-011-cli-operations-contract.md`
8. `docs/decisions/README.md`
9. `tasks/README.md`
10. `tasks/TASK-011-weekly-report.md`
11. `tasks/TASK-012-cli-operations.md`

## 必须执行

1. 核验 main identity `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、分支/HEAD、empty index/worktree 与精确十一文件范围。
2. 对准备文件做两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围核验；字节漂移立即停止。
3. 不运行 uv、pytest、build、imports、数据库、网络、Vault、云端、凭据、launchctl 或任何产品文件 I/O 命令。
4. 将 ADR-010/011 记为 `Accepted`；TASK-011=`READY/UNASSIGNED`，TASK-012=`BLOCKED/UNASSIGNED` 且只依赖 TASK-011 完成后的 CLI 接入。不得预写 TASK-011 的 worktree、角色、Reviewer、merge 或 DONE。
5. 提交信息：`docs: accept weekly reporting and operations contracts`。提交后 main 必须干净，并确认本提示词动态授权解析为本提交。

## 回传格式

```text
Task: ADR-010/011 acceptance sync
Base / Head: <base> -> <head>
ADRs: Accepted
States: TASK-011=READY/UNASSIGNED; TASK-012=BLOCKED/UNASSIGNED
Committed files: <exact eleven>
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
