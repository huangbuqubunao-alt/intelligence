# TASK-009 范围工件清理后复审授权同步 — Status Integrator

你是全新的 Codex Status Integrator。仅提交主控准备的控制面 Markdown，绝不运行产品命令、改 source 业务代码、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@03a5f6ea83ca3c452808d255fffd438cb33c0c78`，必须干净且为唯一父基线。
- Source：`/Users/hua/Documents/yia-worktrees/task-009` / `codex/task-009-obsidian-notes@d16498fe2a1939c6bec7babd03039e623782d027`，必须干净。
- Evidence：`d16498f...` 唯一父为 implementation `956e37a15ab29106f16c45873fccb813cc5a959f`，且只修改 `handoffs/TASK-009.md`。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 `base...source` 仍只允许 TASK-009 的七个路径组。
- Source 的任务/项目状态文档为共同 base 的历史快照；实时状态只以 main 动态包为准。

## 首轮审查与已批准清理

- 首轮 Reviewer 判定 `REJECT` 的唯一原因是 source worktree 内范围外、未跟踪的 `.codebase-memory/` 生成索引工件；没有业务代码 finding，完整 Git Diff 与 fixed diff check 均通过。
- 产品负责人已明确批准且已执行精确清理：`.codebase-memory/.gitattributes`、`artifact.json`、`graph.db.zst`；它们是未跟踪的本地代码索引，不是项目输入或交付物。
- 本包必须重新确认 source 无任何未跟踪/已修改工件；若不干净、范围变化、或任何准备文件字节漂移，立即停止且不覆盖。

## 唯一允许提交范围

1. `agent-prompts/TASK-009-SCOPE-CLEANUP-REREVIEW-INTEGRATOR.md`
2. `agent-prompts/TASK-009-REVIEWER-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-009-obsidian-notes.md`

不得访问或修改 TASK-008 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移、handoff 或其他路径。不得在 TASK-009 source 运行会生成 `.codebase-memory/` 的索引动作；该索引本身是本次已清理的范围外工件。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、empty index/worktree、source 完整范围和 evidence 单文件范围。
2. 仅上述五个准备文件可变；两轮 SHA-256、LF-at-EOF、无尾随空白、`git diff --check`、`git diff --cached --check`、精确暂存范围必须通过。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据、真实或临时产品文件 I/O 命令。
4. main 将 TASK-009 继续标为 `IN_REVIEW`，授权全新独立 Reviewer 2；不得预写 `APPROVE`、`ACCEPTED`、merge 或 `DONE`。
5. 提交信息：`docs: authorize TASK-009 clean-scope rereview`。新提交唯一父必须为固定 main base；提交后 main/source 必须干净，并确认 Reviewer 2 prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-009 scope cleanup / rereview authorization sync
Base / Head: <base> -> <head>
Source/evidence: <source chain>; clean
Committed files: <exact five>
Checks: <git-only gates>
TASK-008 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <unauthorized paths>
```
