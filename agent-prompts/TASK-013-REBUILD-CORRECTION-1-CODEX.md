# TASK-013 rebuild — Codex Implementer Correction 1

你是退回后的原 Codex Implementer。仅修复首轮独立审查 P1-1；不得修改生产代码、CLI/编排、配置、Schema/migration、依赖/锁、测试配置、TASK-013A 或任何其他任务。完成后不得启动 Reviewer、合并、推送、清理 source 或改 main 状态。

## 动态授权与固定对象

- Main authorization：`git -C "/Users/hua/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013-REBUILD-CORRECTION-1-CODEX.md` 必须解析为本 Correction 1 授权提交，且 main 中 TASK-013=`IN_PROGRESS`。
- Source：`/Users/hua/Documents/yia-worktrees/task-013-rebuild` / `codex/task-013-e2e-acceptance-rebuild@3cf8b5fd8e7abec8f8a6595227a8919a7a8804e1`；开始时必须干净。review evidence 的唯一父提交为 `0a9e16887e7dc0b287be941a34e2908766e3992e`，且仅修改 handoff。
- 历史 `task-013` worktree/branch 是已拒绝审计证据，禁止访问、修改或复用。

## 唯一允许产品范围

1. `tests/e2e/test_mvp_flow.py`
2. `tests/e2e/test_failure_recovery.py`
3. `tests/e2e/fixtures/**`
4. `docs/ACCEPTANCE_REPORT.md`
5. `handoffs/TASK-013.md`

## P1-1 修复要求

1. 使用同一 pytest 临时 SQLite、DATA 与 Vault 完成第一次服务流运行后，销毁旧 `_OfflineMvpFlow` 和所有进程内 Fake/服务组合状态。
2. 从同一持久 SQLite/DATA/Vault 重建全新的服务与组合实例；后续恢复、重跑和幂等断言不得依赖旧对象的 `transcripts`、`scores`、`analyses` 或其他进程内字典。
3. 证明重建后可从持久 Artifact、Provider-call、Job/Pipeline 与用户可见文件恢复；Whisper、评分与分析的昂贵 Fake 调用不重复，且 Artifact、Provider-call、笔记、周报不重复。
4. 不得通过通用 handler、直接 `complete_stage`、直接 SQL 更新或伪造最终 Job/Pipeline 代替受测生产服务；只允许最小初始夹具准备。
5. 真实 YouTube、模型/ffmpeg、Ollama/OpenAI/API、凭据、网络、媒体、真实 Vault/用户笔记、付费服务与测试目录外写入均不授权。

## 复用、检查与交付

- Reuse decision：`DIRECT` — 现有项目服务、锁定依赖与 Python 标准库；外部边界仅使用 Fake Adapter；不复制第三方代码或新增依赖。
- 复跑原 TASK-013 离线门禁，并在 handoff/验收报告记录 P1-1 RED/GREEN、重建边界、PRD 10.1–10.8、秘密扫描、复用/许可证、未授权真实路径和剩余风险。
- 提交必须仅在上述五个路径组内，唯一父提交必须为 `3cf8b5fd8e7abec8f8a6595227a8919a7a8804e1`，且 source 必须干净。
