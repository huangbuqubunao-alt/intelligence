# TASK-013A acceptance / final integration authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、修改 source、启动 Integrator、合并、推送或清理。

## 固定对象

- Main base：`main@a8a46afdc393a346ad90016bc9b40301f3c4fd66`，必须干净且为唯一父基线。
- Reviewed source：`/Users/hua/Documents/yia-worktrees/task-013a` / `codex/task-013a-local-transcription-continuation@62d87067af84171a2ee7195f3e7d4c4fddcb9980`，开始时必须干净。
- Review evidence `62d8706...` 的唯一父提交为 Correction 1 `d50c78e9502e3f65018b6af323823c98b3a882ba`，且只修改 `handoffs/TASK-013A.md`；Verdict=`APPROVE`，P0–P3=0。
- 完整产品范围相对 `d96862f...` 不得超过获批四路径；当前实际路径为 `transcripts.py`、本地转写集成测试和 handoff；锁文件不变。

## 唯一允许提交范围

1. `agent-prompts/TASK-013A-ACCEPTANCE-INTEGRATION-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-013A-INTEGRATOR.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013A-local-transcription-continuation.md`

## 必须执行

1. 核验 main/source identity、`user.useConfigOnly=true`、父链、洁净度、review evidence handoff-only 范围、完整产品范围、锁文件不变和 Diff 空白检查。
2. 对五个准备文件做两轮 SHA-256、LF/EOF、无尾随空白、精确暂存范围和 `git diff --cached --check`；任何字节漂移立即停止。
3. main 将 TASK-013A 设为 `ACCEPTED`，记录 Reviewer APPROVE 与 P0–P3=0；不得预写 merge 或 DONE。TASK-013 继续 BLOCKED。
4. Product Integrator authorization 必须动态解析为本次提交；提交信息为 `docs: accept and authorize TASK-013A integration`。
5. 不运行 uv、pytest、mypy、Ruff、build、imports、数据库、网络、模型、媒体、Vault、凭据或任何产品命令。

## 回传格式

```text
Task: TASK-013A acceptance / final integration authorization sync
Base / Head: <base> -> <head>
Review/source/status: <review source> / TASK-013A=ACCEPTED
Committed files: <exact five>
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
