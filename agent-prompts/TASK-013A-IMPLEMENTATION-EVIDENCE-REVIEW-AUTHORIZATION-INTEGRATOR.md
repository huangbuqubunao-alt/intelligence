# TASK-013A implementation evidence / review authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、修改 source、启动 Reviewer、合并、推送或清理。

## 固定对象

- Main base：`main@397e693f02e0e2b0375f8246279d57f7e8031bde`，必须干净且为唯一父基线。
- Source：`/Users/hua/Documents/yia-worktrees/task-013a` / `codex/task-013a-local-transcription-continuation@213c9ff42f9321d443e4e470d74a18a0296ad528`，开始时必须干净。
- Source handoff commit `213c9ff...` 的唯一父提交必须为 implementation `4c3706a969fb85ff4ec344034444d8607894b36f`；implementation 的唯一父提交必须为 `d96862f287d523dd524addf79f86c9b0642a4d31`。
- 产品负责人已批准 ADR-012 方案 2；本轮只授权全新独立 Codex Reviewer 离线审查，不授权真实模型、媒体、网络、凭据或 Vault。

## source 范围

- 相对 `d96862f...`，完整产品范围只能是 `src/youtube_intel/transcripts.py`、`tests/integration/test_local_transcription_service.py`、`tests/unit/test_transcription_policy.py` 与 `handoffs/TASK-013A.md`；本次实际变更允许前三者中的已用三条。
- 禁止 `state.py`、Schema/migration、Provider/CLI/Pipeline composition、依赖/锁文件和 TASK-013 修改。

## 唯一允许提交范围

1. `agent-prompts/TASK-013A-IMPLEMENTATION-EVIDENCE-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-013A-REVIEWER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013A-local-transcription-continuation.md`

## 必须执行

1. 核验 main/source identity、`user.useConfigOnly=true`、父链、洁净度、三路径实际 Diff、四路径最大范围、锁文件不变和所有 Diff 空白检查。
2. 对五个准备文件做两轮 SHA-256、LF/EOF、无尾随空白、精确暂存范围和 `git diff --cached --check`；任何字节漂移立即停止，不覆盖并发改动。
3. main 将 TASK-013A 设为 `IN_REVIEW`；不得预写 APPROVE、ACCEPTED、merge 或 DONE。TASK-013 保持 `BLOCKED/UNASSIGNED`。
4. 动态 Reviewer authorization 必须解析为本次提交；提交信息为 `docs: authorize TASK-013A independent review`。
5. 不运行 uv、pytest、mypy、Ruff、build、imports、数据库、网络、模型、媒体、Vault、凭据或任何产品命令。

## 回传格式

```text
Task: TASK-013A implementation evidence / review authorization sync
Base / Head: <base> -> <head>
Source / status: <source> / TASK-013A=IN_REVIEW
Committed files: <exact five>
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
