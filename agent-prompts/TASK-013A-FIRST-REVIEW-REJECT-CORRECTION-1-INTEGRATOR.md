# TASK-013A first review reject / Correction 1 sync — Status Integrator

你是全新的 Codex Status Integrator。只提交主控准备的控制面 Markdown；不得运行产品命令、修改 source、启动 Worker、合并、推送或清理。

## 固定对象

- Main base：`main@d47dfdad12b99b001e6d2fc295a905cbd882c868`，必须干净且为唯一父基线。
- Source evidence：`/Users/developer/Documents/yia-worktrees/task-013a` / `codex/task-013a-local-transcription-continuation@08542b84d550ca225dece520cf748a2fc654ab58`，开始时必须干净。
- Evidence `08542b...` 的唯一父提交为 `213c9ff42f9321d443e4e470d74a18a0296ad528`，且只修改 `handoffs/TASK-013A.md`；完整产品范围相对 `d96862f...` 不得超过获批四路径。
- 该 evidence 的 Verdict=`REJECT`，P1：缓存 canonical Artifact 未验证历史 Job/Pipeline provenance，篡改 `artifacts.job_id` 可推进错误的运行 Job。

## Correction 1 source 唯一允许路径

1. `src/youtube_intel/transcripts.py`
2. `tests/integration/test_local_transcription_service.py`
3. `handoffs/TASK-013A.md`

不得修改 `state.py`、Schema/migration、`providers/whisper.py`、`transcription.py`、Pipeline/CLI composition、依赖/锁文件或 TASK-013。真实模型、ffmpeg、媒体/YouTube、网络、Ollama/OpenAI、真实 Vault、凭据和付费服务继续不授权。

## 唯一允许提交范围

1. `agent-prompts/TASK-013A-FIRST-REVIEW-REJECT-CORRECTION-1-INTEGRATOR.md`
2. `agent-prompts/TASK-013A-CORRECTION-1-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013A-local-transcription-continuation.md`

## 必须执行

1. 核验 main/source identity、`user.useConfigOnly=true`、父链、洁净度、evidence handoff-only 范围、完整四路径范围、锁文件不变和 Diff 空白检查。
2. 对五个准备文件做两轮 SHA-256、LF/EOF、无尾随空白、精确暂存范围和 `git diff --cached --check`；任何字节漂移立即停止，不覆盖并发改动。
3. main 将 TASK-013A 设为 `IN_PROGRESS`，原 Codex Implementer 执行 Correction 1；记录 P1 与三路径边界。不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-013 继续 BLOCKED。
4. 动态 Correction authorization 必须解析为本次提交；提交信息为 `docs: return TASK-013A for cache provenance correction`。
5. 不运行 uv、pytest、mypy、Ruff、build、imports、数据库、网络、模型、媒体、Vault、凭据或任何产品命令。

## 回传格式

```text
Task: TASK-013A first review reject / Correction 1 sync
Base / Head: <base> -> <head>
Source / status: <source> / TASK-013A=IN_PROGRESS
Committed files: <exact five>
Checks: <Git-only gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
