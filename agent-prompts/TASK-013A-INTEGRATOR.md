# TASK-013A — Product Integrator

你是独立的 Codex Product Integrator。只把已验收 source 用 `--no-ff` 合并到 main，并复跑授权的离线门禁；不得修改产品代码、测试、任务状态或 source，不得修复冲突以外的问题。若存在冲突、范围扩大、门禁失败或 main/source 非干净，停止并报告。

## 固定对象

- Execution base：动态读取 `git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013A-INTEGRATOR.md`，必须为本授权提交，且 main 中 TASK-013A=`ACCEPTED`。
- Accepted source：`/Users/hua/Documents/yia-worktrees/task-013a` / `codex/task-013a-local-transcription-continuation@62d87067af84171a2ee7195f3e7d4c4fddcb9980`；必须干净。
- Source review evidence `62d8706...` 的唯一父提交为 `d50c78e...`；完整产品范围相对 `d96862f...` 最多四路径，实际仅：
  1. `src/youtube_intel/transcripts.py`
  2. `tests/integration/test_local_transcription_service.py`
  3. `tests/unit/test_transcription_policy.py`（允许为空）
  4. `handoffs/TASK-013A.md`
- 不得修改依赖/锁、Schema/migration、`state.py`、Provider/Pipeline/CLI composition、TASK-013 或其他任务。

## 合并与检查

1. 核验 identity `Mozhu <huangbuqubunao@gmail.com>`、`user.useConfigOnly=true`、main/source 固定 SHA、洁净度、父链、范围、锁文件和 `git diff --check`。
2. 在 main 以 `git merge --no-ff 62d87067af84171a2ee7195f3e7d4c4fddcb9980` 创建双父提交；不得 rebase、cherry-pick、push、清理 source 或改任务状态。若无冲突仍必须保留 merge commit。
3. 在合并结果执行：

```bash
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/integration/test_local_transcription_service.py
uv run python -m pytest tests/unit/test_transcription_policy.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
```

4. 验证 sdist/wheel 包含 `youtube_intel/migrations/001_initial.sql`；清理本轮忽略 `dist/` 构建产物（仅本轮产生的文件）。
5. 验证 merge 恰有两个父、父顺序为 execution base + accepted source、accepted source 成为 main 祖先、first-parent Diff 精确为实际三条产品路径，锁文件未变，main/source 都干净。

## 资源边界

仅离线 Fake executor、临时 SQLite/DATA 和锁定依赖。不得下载/加载模型、运行 ffmpeg、媒体/YouTube、网络、Ollama/OpenAI、真实 Vault/用户笔记、凭据、付费调用或测试目录外写入。

## 回传格式

```text
Task: TASK-013A
Role: Product Integrator
Execution base: <sha>
Source head: 62d87067af84171a2ee7195f3e7d4c4fddcb9980
Merge commit: <sha>
Merge parents: <base>, <source>
Checks: <results>
Post-merge task status: ACCEPTED (not DONE)
Verdict: INTEGRATED | BLOCKED
```
