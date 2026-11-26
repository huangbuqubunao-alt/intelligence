# TASK-013A Correction 1 review authorization sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、修改 source、启动 Reviewer、合并、推送或清理。

## 固定对象

- Main base：`main@07b5f559cb47d43b761cb3444636213a65fc7cf3`，必须干净且为唯一父基线。
- Correction source：`/Users/developer/Documents/yia-worktrees/task-013a` / `codex/task-013a-local-transcription-continuation@d50c78e9502e3f65018b6af323823c98b3a882ba`，开始时必须干净。
- Correction `d50c78e...` 的唯一父提交必须为 `08542b84d550ca225dece520cf748a2fc654ab58`；Correction 只允许 `transcripts.py`、本地转写集成测试和 handoff。完整产品范围相对 `d96862f...` 不得超过获批四路径。

## 唯一允许提交范围

1. `agent-prompts/TASK-013A-CORRECTION-1-REVIEW-AUTHORIZATION-INTEGRATOR.md`
2. `agent-prompts/TASK-013A-REVIEWER-2-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013A-local-transcription-continuation.md`

## 必须执行

1. 核验 main/source identity、`user.useConfigOnly=true`、父链、洁净度、Correction 三路径与完整四路径范围、锁文件不变和 Diff 空白检查。
2. 对五个准备文件做两轮 SHA-256、LF/EOF、无尾随空白、精确暂存范围和 `git diff --cached --check`；任何字节漂移立即停止。
3. main 将 TASK-013A 设为 `IN_REVIEW`，授权全新独立 Codex Reviewer 复跑所有离线门禁、P1 provenance 矩阵、原子性/缓存/补偿探针和完整 AC/ADR-012 矩阵；不得预写 Verdict、ACCEPTED、merge 或 DONE。TASK-013 继续 BLOCKED。
4. 动态 Reviewer authorization 必须解析为本次提交；提交信息为 `docs: authorize TASK-013A cache provenance review`。
5. 不运行 uv、pytest、mypy、Ruff、build、imports、数据库、网络、模型、媒体、Vault、凭据或任何产品命令。

## 回传格式

```text
Task: TASK-013A Correction 1 review authorization sync
Base / Head: <base> -> <head>
Source / status: <source> / TASK-013A=IN_REVIEW
Committed files: <exact five>
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
