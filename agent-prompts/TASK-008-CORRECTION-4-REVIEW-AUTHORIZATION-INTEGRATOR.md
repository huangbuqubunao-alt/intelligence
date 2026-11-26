# TASK-008 Correction 4 复审授权同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理 worktree。

## 固定对象

- Main base：`main@27c9ded10f1d3b930b6f70f2da185232916a98dc`，必须干净且为唯一父基线。
- Source：`/Users/developer/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@bb195a59ddee25cb804b0078676c504e94c44441`，必须干净且无 `.codebase-memory/` 或其他未跟踪工件。
- Correction 4：唯一父为 reviewer-4 evidence `19323923057adb0b5a9f59cac5eb7c32cce5888a`，精确修改 `analysis.py`、`test_summary_provider.py` 和 source handoff。
- Original base：`473119704c7638d7afd4e68d84d00e85064ceabd`；完整 Diff 仅为 TASK-008 七个批准路径组中的六个实际路径。
- Source 的任务/项目状态为分配前冻结快照；实时状态仅以 main 本提交为准。

## 实现证据与审查边界

- Implementer 自报 Correction 4 在 `complete_stage` 前验证成功 ProviderCall 请求身份、raw/structured Artifact 元数据和文件 SHA-256、以及解析结果 request hash/provider/model；不匹配 fail-closed。
- 新增十个真实临时 SQLite + Fake transport 篡改/缺失缓存回归；focused=`4/24`、full pytest=`355`、mypy、Ruff、CLI、locked sync、offline build 与 sdist/wheel inclusion 自报 PASS。这些仅为待独立复跑证据。
- 第五位独立 Reviewer 仅可追加 source handoff，复跑全部离线门禁和缓存完整性/副作用/原子恢复探针；不得改业务代码、依赖、锁、main 或任务状态。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-CORRECTION-4-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-008-REVIEWER-5-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

不得访问或修改 TASK-009 source/worktree，也不得暂存产品代码、依赖、锁、Schema、迁移或 handoff。

## 必须执行

1. 核验 main/source branch、HEAD、父链、身份 `Mozhu <maintainer@example.invalid>`、`user.useConfigOnly=true`、empty index/worktree、Correction 3/4 和完整 source 范围。
2. 准备文件仅限上述五个路径；两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围必须通过；字节漂移立即停止。
3. 不运行 uv、pytest、build、import、数据库、网络、Vault、云端、凭据或任何产品文件 I/O 命令。
4. main 将 TASK-008 设为 `IN_REVIEW`，授权全新独立 Reviewer 5；不得预写 Verdict、ACCEPTED、merge 或 DONE。TASK-009 必须保持 `IN_PROGRESS` 且未触碰。
5. 提交信息：`docs: authorize TASK-008 cache integrity review`。提交后 main/source 必须干净，并确认 Reviewer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-008 Correction 4 review authorization sync
Base / Head: <base> -> <head>
Source/correction/status: <chain>; TASK-008=IN_REVIEW
Committed files: <exact five>
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <unverified correction / unauthorized paths>
```
