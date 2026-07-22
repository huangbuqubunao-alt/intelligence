# TASK-008 首次审查拒绝与 Correction 1 同步 — Status Integrator

你是全新的 Codex Status Integrator。只提交主控已准备的控制面 Markdown；不得运行产品命令、改 source、合并、推送或清理任何 worktree。

## 固定对象

- Main base：`main@d44477bd0fa945383769b83f3672d1c606f3c365`；必须是干净单父基线。
- Source：`/Users/hua/Documents/yia-worktrees/task-008` / `codex/task-008-deep-analysis@b61f46f6bca3303d5590aac76d8c8c9b53ec4131`，必须干净。
- 审查 evidence：`b61f46f...` 的唯一父必须为 implementation `10478a9083df4eedae061d99d941c88cb4954179`，且 evidence 只改 `handoffs/TASK-008.md`。
- 固定原始 base：`473119704c7638d7afd4e68d84d00e85064ceabd`；`base...source` 完整范围只能是 TASK-008 的七个批准路径组。
- Source 中的任务卡和项目状态为分配前冻结快照；实时状态仅以 main 本提交为准。

## 唯一允许提交范围

1. `agent-prompts/TASK-008-FIRST-REVIEW-REJECT-CORRECTION-1-INTEGRATOR.md`
2. `agent-prompts/TASK-008-CORRECTION-1-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-008-deep-analysis.md`

不得触碰 TASK-009 source/worktree，或任何产品文件、依赖、锁、Schema、迁移、任务 handoff。

## 审查拒绝事实

- Verdict=`REJECT`；P0=0，P1=1。
- P1：`RepositoryBackedAnalysisService.analyze` 绕过本地 token 上限门禁；最大输入 token 设为 `1` 时，临时 SQLite + Fake Provider/Resolver 仍发生 `provider=1`、`credential=1`。这违反 token 超限零调用与凭据最后读取要求。
- Reviewer 依工作包在 P1 处停止；未运行的其余门禁不得表述为通过。

## 必须执行

1. 先确认 main/source 分支、HEAD、身份 `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、干净 index/worktree 和上述父链/范围。
2. 确认准备文件仅为上述五个路径；记录 SHA-256，检查后再次核对，若任何字节变化立即停止、不覆盖。
3. `git diff --check`、LF/EOF、tailing whitespace、`git diff --cached --check` 和暂存范围必须通过。
4. 不运行 uv、pytest、build、import、数据库、网络、模型、Vault、凭据或文件删除命令。
5. 提交信息：`docs: return TASK-008 for token gate correction`。新提交唯一父必须是固定 main base。
6. 提交后确认 main/source 干净、source HEAD 未变，以及 `git log -1 --format=%H -- agent-prompts/TASK-008-CORRECTION-1-CODEX.md` 解析为本提交。

## 状态结果

- main 将 TASK-008 退回原 Codex Implementer 的 `IN_PROGRESS`，冻结 Correction 1；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。
- TASK-009 必须保持 `IN_REVIEW` 且未触碰。
- Correction 1 只授权 source `analysis.py`、`tests/unit/test_analysis_policy.py`、`tests/integration/test_summary_provider.py` 和 `handoffs/TASK-008.md`：持久化路径必须在任何凭据读取、Provider/transport 或 Repository 写入前执行同一确定性本地 token 上限门禁；超限必须是零调用。必须新增临时 SQLite + Fake Provider/Resolver 回归，覆盖 token 上限为 1 的普通字幕。
- 仍禁止真实 OpenAI、密钥、付费/API 调用、任何网络、云端 token-count、用户内容、媒体、YouTube、Vault、依赖/锁、Schema/migration、`state.py`、CLI 和 TASK-009。

## 回传格式

```text
Task: TASK-008 first review reject / Correction 1 sync
Base / Head: <base> -> <head>
Committed files: <exact five>
Source/evidence/status: <SHA chain>; TASK-008=IN_PROGRESS
Checks: <git-only gates>
TASK-009 untouched: yes
Verdict: INTEGRATED | BLOCKED
Remaining risks: <P1 / unauthorized paths>
```
