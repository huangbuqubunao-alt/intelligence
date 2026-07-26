# TASK-013 rebuild — Correction 1 Independent Codex Reviewer

你是全新的、独立的 Codex Reviewer。审查 Correction 1 是否关闭首轮审查的 P1-1：同一临时持久状态上的真实组合重建、重启恢复与昂贵调用缓存。不得修改业务代码、测试、验收报告、依赖、锁文件、任务状态、main 或其他任务；只可向 source 的 `handoffs/TASK-013.md` 追加审查证据并创建 handoff-only commit。

## 动态授权与审查对象

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013-REBUILD-CORRECTION-1-REVIEWER-CODEX.md` 必须解析为本审查授权提交，且 main 中 TASK-013=`IN_REVIEW`。
- Reviewed source：`/Users/hua/Documents/yia-worktrees/task-013-rebuild` / `codex/task-013-e2e-acceptance-rebuild@ae724990f6f3628a054bfca000e9e28d83f3def7`；开始时必须干净，唯一父提交为 `3cf8b5fd8e7abec8f8a6595227a8919a7a8804e1`。
- 相对 original base `2a59dfe3860161a5989f2c08161f03c73aa4ca86` 只允许：`tests/e2e/test_mvp_flow.py`、`tests/e2e/test_failure_recovery.py`、`tests/e2e/fixtures/**`、`docs/ACCEPTANCE_REPORT.md`、`handoffs/TASK-013.md`。
- 历史 `task-013` worktree/branch 是已拒绝审计证据，禁止访问或修改。

## 独立验证

1. **销毁与重建**：首次运行后确认旧服务、Repository、Fake Provider、`_OfflineMvpFlow` 和进程内缓存均不可参与后续断言；以相同 pytest 临时 SQLite/DATA/Vault 重建完整的新组合，且新内存缓存为空。
2. **持久恢复与缓存**：只从 Artifact、Provider-call、Job/Pipeline 和用户可见文件恢复。重建后的新 Fake Whisper、评分、分析及其他昂贵边界调用均为 `0`；Artifact、Provider-call、笔记和周报不重复。
3. **失败恢复与稳定重跑**：独立复核字幕、转写、评分、分析、笔记、周报边界失败后恢复；稳定重跑不产生新昂贵调用或用户可见副作用。
4. **无捷径/范围**：不得用通用 handler、直接 `complete_stage`、直接 SQL 更新、直接推进 SQLite 状态或伪造最终 Job/Pipeline 代替生产服务；只允许最小初始夹具。确认未改生产代码、CLI/编排、配置、Schema/migration、依赖/锁或测试配置。
5. **资源与隐私**：真实 YouTube、模型/ffmpeg、Ollama/OpenAI/API、网络、凭据、真实 Vault、媒体、付费服务和测试目录外写入均未授权。复核 Fake/临时目录、秘密扫描、PRD 10.1–10.8、复用和许可证证据。

## 必跑离线门禁

```bash
uv lock --check
uv sync --locked --offline
uv run python -m pytest tests/e2e -m 'not network and not cloud'
uv run python -m pytest tests/e2e/test_mvp_flow.py
uv run python -m pytest tests/e2e/test_failure_recovery.py
uv run python -m pytest
uv run mypy src
uv run ruff check .
uv run python -m youtube_intel --help
uv build --offline
git diff --check 2a59dfe3860161a5989f2c08161f03c73aa4ca86...HEAD
```

若发现 P0/P1，立即停止未开始的无关门禁或探针，记录已执行/跳过项；不得自行修复。结束时只在 handoff 写入矩阵、P0–P3、范围、复用/许可证、未授权路径和 `APPROVE` 或 `REJECT`。如提交证据，唯一父提交必须为 `ae724990f6f3628a054bfca000e9e28d83f3def7`，且只修改 `handoffs/TASK-013.md`。
