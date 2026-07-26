# TASK-013A assignment sync — Worktree / Status Integrator

你是全新的 Codex Worktree / Status Integrator。只创建获批 worktree/branch 并提交主控准备的控制面 Markdown；不得运行产品命令、修改 source、启动 Implementer/Reviewer、合并、推送或清理。

## 固定对象

- Main base：`main@d96862f287d523dd524addf79f86c9b0642a4d31`，必须干净且为唯一父基线。
- 目标 worktree：`/Users/hua/Documents/yia-worktrees/task-013a`；目标分支：`codex/task-013a-local-transcription-continuation`。两者开始时必须不存在。
- 产品负责人已批准 ADR-012 方案 2：Codex 是唯一 Implementer；完成后由全新独立 Codex Reviewer 审查。
- TASK-013 保持 `BLOCKED/UNASSIGNED`；不得创建、读取或修改其 worktree。

## source 唯一允许路径

1. `src/youtube_intel/transcripts.py`
2. `tests/integration/test_local_transcription_service.py`
3. `tests/unit/test_transcription_policy.py`
4. `handoffs/TASK-013A.md`

不得修改 `state.py`、Schema/migration、`providers/whisper.py`、`transcription.py`、Pipeline/CLI composition、依赖或锁文件。不得下载/加载模型，调用 ffmpeg、媒体/YouTube、网络、Ollama/OpenAI、真实 Vault/用户笔记、凭据或付费服务。只允许 pytest 临时 SQLite/DATA 与 Fake Whisper executor。

## 唯一允许提交范围

1. `agent-prompts/TASK-013A-ASSIGNMENT-INTEGRATOR.md`
2. `agent-prompts/TASK-013A-IMPLEMENTER-CODEX.md`
3. `docs/PROJECT_STATUS.md`
4. `tasks/README.md`
5. `tasks/TASK-013A-local-transcription-continuation.md`

## 必须执行

1. 核验 main identity `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、分支/HEAD、empty index/worktree、目标路径/分支不存在与精确五文件范围。
2. 从固定 base 创建目标 branch/worktree，核验 branch、HEAD 与洁净度。source 内 `READY/UNASSIGNED` 是固定 base 快照；实时控制面只在 main。
3. 对准备文件做两轮 SHA-256、LF/EOF、无尾随空白、`git diff --check`、`git diff --cached --check` 与精确暂存范围核验；字节漂移立即停止。
4. main 将 TASK-013A 设为 `IN_PROGRESS/Codex`，记录 worktree、分支、base、四文件范围和资源边界；不得预写 Reviewer verdict、ACCEPTED、merge 或 DONE。TASK-013 保持 BLOCKED。
5. 提交信息：`docs: assign TASK-013A transcription continuation worktree`。提交后 main/source 必须干净，确认 Implementer prompt 的动态授权解析为本提交。

## 回传格式

```text
Task: TASK-013A assignment sync
Base / Head: <base> -> <head>
Worktree/branch/base: <path> / <branch> / <base>
Committed files: <exact five>
States: TASK-013A=IN_PROGRESS/Codex; TASK-013=BLOCKED/UNASSIGNED
Checks: <Git-only/worktree gates>
Product commands: not run
Verdict: INTEGRATED | BLOCKED
```
