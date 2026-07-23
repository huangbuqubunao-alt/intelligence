# TASK-008 Correction 5 复审授权同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@8614735ea8a9c0e347cf9fceaa6f5a25549e7813`，必须干净且为唯一父基线。
- Source：`/Users/hua/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@dcbbd38fe8bab79fd6db1679f43a8ca48fb472ea`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Correction 5：唯一父为 reviewer-5 evidence `78ae101786ada5f04d2b7c734c84a216f8820803`，精确修改 `providers/cloud_llm.py`、`test_summary_provider.py` 和 source handoff。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-008 七个批准路径组中的六个实际路径。
- Source 的任务/项目状态为分配前冻结快照；实时状态仅以 main 本提交为准。

## 实现证据与审查边界

- Implementer 自报隔离 child 的握手、写入、响应读取与退出使用有限 deadline；所有失败关闭管道并有限 terminate/kill/reap。
- 新增离线 Fake child 回归覆盖卡住握手/响应、EOF、畸形 JSON、非零退出和正常响应；focused=`4/30`、full pytest=`361`、mypy、Ruff、CLI、locked sync、offline build 与 sdist/wheel inclusion 自报 PASS。这些仅为待独立复跑证据。
- 第六位独立 Reviewer 仅可追加 source handoff，复跑全部离线门禁和 A-17 收口、缓存完整性、A-03 零副作用与原子恢复探针；不得改业务代码、依赖、锁、main 或任务状态。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-CORRECTION-5-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-008-REVIEWER-6-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

不得访问或修改 TASK-009 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、empty index/worktree、Correction 5 和完整 source 范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-008 设为 `IN_REVIEW`，授权全新独立 Reviewer 6；不得预写 Verdict、ACCEPTED、merge 或 DONE。TASK-009 必须保持 `IN_PROGRESS` 且未触碰。
5. 提交信息：`docs: authorize TASK-008 subprocess review`。提交后 main/source 必须干净，并确认 Reviewer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-008 Correction 5 review authorization sync
Base / Head: <base> -> <head>
Source/correction/status: <chain>; TASK-008=IN_REVIEW
Committed files: <exact five>
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <unverified correction / unauthorized paths>
```
