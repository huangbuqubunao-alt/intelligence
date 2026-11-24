# TASK-009A 实现证据与独立审查授权同步 — Status Integrator

你是全新的 Codex Status Integrator。你只提交主控准备的 TASK-009A 审查授权控制面；不得实现、审查、安装依赖、运行 `uv`、pytest、mypy、Ruff、build、网络、Vault、数据库或产品命令，不得修改 source、启动 Reviewer、合并、push 或清理。

## 固定事实

- main Required base：`c5a132cfd889e05ee86aad41429e1abacedc4982`
- Source worktree/branch：`/Users/developer/Documents/yia-worktrees/task-009a` / `codex/task-009a-obsidian-note-shared-contracts`
- Source implementation：`75158be08d6442a7b18099f459654e9da86ebcee`
- Source parent/base：`e4271e41910bba54b37b48df709dcf632fe3b0eb`
- 身份：`Mozhu <maintainer@example.invalid>`，`user.useConfigOnly=true`。

## 唯一允许提交范围

仅以下五个主控预写 Markdown 文件：

1. `agent-prompts/TASK-009A-IMPLEMENTATION-EVIDENCE-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-009A-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-009A-obsidian-note-shared-contracts.md`

初始 main 必须在 Required base、暂存区为空、工作树只含上述五个预写变更；source 必须处于固定 implementation SHA 且干净。准备文件 SHA-256 在两轮检查中变化、任何范围外/并发变更、源父链或范围异常均立即 `BLOCKED`，不得覆盖、取消暂存或清理。

## 必须核验

1. source `75158...` 只有父 `e427...`，相对 base 精确为：`domain.py`、`test_contracts.py`、`pyproject.toml`、`uv.lock`、`handoffs/TASK-009A.md`；所有 Diff whitespace 均通过。
2. 直接依赖精确包含 `Jinja2>=3.1.6,<3.2`，必要传递边界仅为解析出的 `MarkupSafe`；既有直接依赖不得升级。实现者检查 `contracts 74`、全量 `326`、mypy、Ruff、CLI、lock/sync、offline build/migration inclusion 均仅是待独立复跑的证据。
3. main 控制面将 TASK-009A 设为 `IN_REVIEW`，固定 source SHA 和全新独立 Codex Reviewer；不得预写 `APPROVE`、`ACCEPTED`、merge 或 `DONE`。
4. TASK-008A 保持 `DONE`；TASK-008/TASK-009 和下游继续 `BLOCKED/UNASSIGNED`；真实 Vault、用户笔记、文件 I/O、云端/凭据仍未授权。

执行分支/身份/索引/source/范围/依赖声明/锁文件、LF/EOF、尾随空白、`git diff --check`、暂存范围、`git diff --cached --check`、提交范围/父链和最终 main/source 洁净度；不运行产品命令。

仅当全部通过时，创建唯一单父提交：

```text
docs: authorize TASK-009A independent review
```

回传 Task、Role、Base/Head、identity、精确文件范围、source/status、静态核验、Post-commit status、Verdict 与 remaining risks。
