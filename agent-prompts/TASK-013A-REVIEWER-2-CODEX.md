# TASK-013A — Second Independent Codex Reviewer

你是全新的、独立的 Codex Reviewer。审查 Correction 1 是否消除了“缓存关联错误历史任务”的 P1，且没有破坏真实的本地转写、缓存恢复、数据库补偿或 DATA 安全边界。不得修改业务代码、测试、依赖、锁文件、任务状态、main 或其他任务；只可向 source 的 `handoffs/TASK-013A.md` 追加审查证据并创建 handoff-only commit。

## 固定对象与授权

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013A-REVIEWER-2-CODEX.md` 必须解析为本审查授权提交，且 main 中 TASK-013A=`IN_REVIEW`。
- Reviewed source：`/Users/hua/Documents/yia-worktrees/task-013a` / `codex/task-013a-local-transcription-continuation@d50c78e9502e3f65018b6af323823c98b3a882ba`；开始时必须干净，唯一父提交为 `08542b84d550ca225dece520cf748a2fc654ab58`。
- Correction 范围严格为 `src/youtube_intel/transcripts.py`、`tests/integration/test_local_transcription_service.py`、`handoffs/TASK-013A.md`；完整范围相对 `d96862f287d523dd524addf79f86c9b0642a4d31` 不超过获批四路径。
- 模型下载/加载、ffmpeg、媒体/YouTube、网络、Ollama/OpenAI、真实 Vault/用户笔记、凭据、付费服务和测试目录外写入均未授权。

## 必读材料

完整阅读 `AGENTS.md`、协作/状态/PRD/System Design/Reuse Register、TASK-013A、ADR-012、Correction 1 prompt 与本包。不得运行会生成 `.codebase-memory/` 的索引；没有代码图工具时可用只读 `rg`。

## 独立探针

1. **P1 provenance 矩阵**：先用产品 `LocalTranscriptionService` 成功持久化，再分别使 canonical Artifact 的历史 Job 缺失、空白、未知、RUNNING、FAILED、非 TRANSCRIPT、其他 video 或其他 pipeline version。每种情况均须在 executor、当前 Job/Pipeline、Artifact/Provider-call 或 cleanup 副作用前 fail-closed。
2. **可信缓存恢复**：同一 video、同一 pipeline version、已成功完成的历史 TRANSCRIPT Job 仍可给一个已领取的重排 Job 恢复；Fake executor 零调用，不新增 Artifact/Provider-call，当前 Job/Pipeline 正常完成。
3. **原始服务承诺**：使用真实临时 SQLite/DATA 与 Fake executor 核对成功原子完成、音频/路径/hash/symlink 拒绝、`complete_stage` 失败补偿、Provider-call 可重试和成功后受控 cleanup。明确 cleanup 仅为 at-most-once best effort。
4. **范围/资源**：确认不改 state/Schema/Provider/Pipeline/CLI/依赖/锁文件，也不运行任何模型或真实资源。复核仅使用既有 `mlx-whisper` Adapter 和标准库，许可证/模型资源风险仍留 TASK-014。
5. **验收矩阵**：判定 TASK-013A AC-1–AC-5、ADR-012 C-01–C-05、P0–P3 和 Verdict。

## 必须复跑的离线门禁

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
git diff --check d96862f287d523dd524addf79f86c9b0642a4d31...HEAD
```

发现 P0/P1 后，按工作包立即停止未开始的无关门禁或探针，记录已执行/跳过项；不得自行修复。结束时只在 handoff 写证据、矩阵、P0–P3、范围/复用/许可证、未授权路径和 `APPROVE` 或 `REJECT`。如提交证据，唯一父提交必须为 `d50c78e9502e3f65018b6af323823c98b3a882ba`，且只修改 `handoffs/TASK-013A.md`。
