# TASK-013 rebuild — Codex Implementer Correction 2

你是退回后的原 Codex Implementer。仅修复第二轮独立审查 P1-1：失败阶段在销毁原组合后无法从持久状态恢复。不得修改生产代码、CLI/编排、配置、Schema/migration、依赖/锁、测试配置、TASK-013A 或任何其他任务。完成后不得启动 Reviewer、合并、推送、清理 source 或改 main 状态。

## 动态授权与唯一谱系

- Main authorization：`git -C "/Users/developer/Documents/youtubek agent" log -1 --format=%H -- agent-prompts/TASK-013-REBUILD-CORRECTION-2-CODEX.md` 必须解析为本 Correction 2 授权提交，且 main 中 TASK-013=`IN_PROGRESS`。
- 唯一 source：`/Users/developer/Documents/yia-worktrees/task-013-rebuild` / `codex/task-013-e2e-acceptance-rebuild@4aecab7c3f88f0a108ee815c05436d12dd0dfdd8`；开始时必须干净。review evidence 的唯一父提交为 `ae724990f6f3628a054bfca000e9e28d83f3def7`，且只修改 handoff。
- 历史 `task-013` worktree/branch 是已拒绝审计证据，禁止访问、修改或复用。

## 唯一允许产品范围

1. `tests/e2e/test_mvp_flow.py`
2. `tests/e2e/test_failure_recovery.py`
3. `tests/e2e/fixtures/**`
4. `docs/ACCEPTANCE_REPORT.md`
5. `handoffs/TASK-013.md`

## P1-1 修复要求

1. 测试不得以 `_OfflineMvpFlow` 的内存 `transcripts`、`scores`、`analyses` 或任何旧 Repository、Fake Provider、计数器作为重启恢复依据。
2. 第一次失败后必须销毁整个组合，并在同一 pytest 临时 SQLite/DATA/Vault 上重建全新的组合；恢复只可读取并验证持久 SQLite 与 Artifact、Provider-call、Job/Pipeline 和用户可见文件。
3. 至少证明：**评分失败 → 进程重启 → 保留已验证转写 → 只执行必要评分 → 后续笔记/周报完成**。新组合不得重复 Whisper 或其他已满足持久缓存的昂贵调用；稳定重跑也不得重复 Artifact、Provider-call、笔记或周报。
4. 对其他适用失败边界也必须在新组合中证明恢复或明确终态，不能仅保留同进程 retry；不得使用通用 handler、直接 `complete_stage`、直接 SQL 更新、直接推进 SQLite 状态或伪造最终 Job/Pipeline。
5. 真实 YouTube、模型/ffmpeg、Ollama/OpenAI/API、凭据、网络、媒体、真实 Vault/用户笔记、付费服务与测试目录外写入均不授权。

## 复用、检查与交付

- Reuse decision：`DIRECT` — 现有项目服务、锁定依赖与 Python 标准库；外部边界仅使用 Fake Adapter；不复制第三方代码或新增依赖。
- 复跑原 TASK-013 离线门禁，并在 handoff/验收报告记录 P1-1 RED/GREEN、失败后组合销毁、第二次完整组合、持久恢复、各昂贵 Fake 调用、PRD 10.1–10.8、秘密扫描、复用/许可证、未授权真实路径和剩余风险。
- 提交必须仅在上述五个路径组内，唯一父提交必须为 `4aecab7c3f88f0a108ee815c05436d12dd0dfdd8`，且 source 必须干净。
