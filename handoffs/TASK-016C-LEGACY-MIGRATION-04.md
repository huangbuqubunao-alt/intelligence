# TASK-016C Legacy Migration-04 — State Store Trusted Flow Cutover

## 元数据

- Task: `TASK-016C Legacy Migration-04`
- Role: `Implementer`
- Agent/session: `Codex / root`
- Base branch/commit: `workbuddy/task-016c-content-quality-layer@778a2758147ec20895bf93f5fa567fd0a4c0f757`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-016c-content-quality-layer`
- Branch: `workbuddy/task-016c-content-quality-layer`
- Started: `2026-08-23T02:36:00Z`
- Reported: `2026-08-23T02:41:34Z`

## 目标与范围

- 任务目标：将 state-store integration scoring tests 从 legacy
  `complete_stage(TRANSCRIPT_READY -> SCORED)` 切换至 Phase G trusted
  persistence flow。
- 允许修改：`tests/integration/test_state_store.py` 和必要 integration helper。
- 实际修改：`tests/integration/test_state_store.py`；本交接证据。
- 明确未做：未修改 `src/youtube_intel/{scoring,runtime,state}.py`、schema、migration、
  dependencies、`uv.lock` 或 `tests/unit/test_task016c_phase_g.py`；未进入 Phase H。

## 验收证据

| 验收项 | PASS/FAIL/BLOCKED | 证据 |
|---|---|---|
| Legacy dependency removal | PASS | 已删除两个 legacy scoring-success tests 的 manual Artifact/ProviderCall completion/summary 写入。唯一保留的 direct scoring `complete_stage` 调用是负向测试，传入空 artifacts、无 ProviderCall、无 summary，并断言在 runtime trusted-entry guard 处失败。 |
| Trusted scoring flow | PASS | 新 helper 以 fake PRIMARY provider 和 fake local quality judge 配置 `RuntimeOperations`；`run_primary_trusted_scoring()` 产生 exact `PhaseFTrustedScoringSuccess`，runtime-owned `TrustedPersistenceEntry.persist_success()` 生成 `SCORING_RAW`、`SCORING_STRUCTURED`、两条 `SUCCEEDED` ProviderCall、`Video.SCORED` 和 `Job.SUCCEEDED`。 |
| summary 缺失/legacy path | PASS | `test_legacy_scoring_completion_without_summary_fails_before_writes` 证明旧调用没有 summary 时被拒绝，文件快照不变，Artifact/ProviderCall 均为零，Video 仍 `TRANSCRIPT_READY`，Job 仍 `RUNNING`。 |
| 原子性与 rollback | PASS | `atomic_register.after_pipeline` 注入故障后，SQLite transaction rollback：零 Artifact、零 ProviderCall、Video 未评分、Job 未成功。按 Phase G 固定协议，已 promote 但未登记的 final files 被保留为 H 的 future recovery 输入，而非 partial success。 |
| 幂等性 | PASS | 同一个 in-memory success 第二次 `persist_success()` 返回相同结果；SQLite 仍为两个 Artifact、两个 ProviderCall，filesystem 仍为两个 JSON outputs。 |

## Reuse decision

- `DIRECT`：使用仓库已批准的 Phase G production interfaces
  `RuntimeOperations.run_primary_trusted_scoring()` 与
  `TrustedPersistenceEntry.persist_success()`；无新增第三方代码、依赖或许可证义务。

## 检查结果

| 命令/人工检查 | 结果 | 关键输出或说明 |
|---|---|---|
| `.venv/bin/ruff check tests/integration/test_state_store.py` | PASS | `All checks passed!` |
| `.venv/bin/pytest tests/integration/test_state_store.py -q` | PASS | `36 passed` |
| `.venv/bin/pytest tests/integration/test_pipeline.py -q` | PASS | `15 passed` |
| `.venv/bin/pytest tests/integration/test_ollama_provider.py -q` | PASS | `72 passed` |
| `.venv/bin/pytest tests/e2e/test_mvp_flow.py -q` | PASS | `3 passed` |
| `.venv/bin/pytest tests/unit/test_task016c_phase_g.py -q` | PASS | `76 passed` |
| `.venv/bin/pytest -x -q` | BLOCKED | `376 passed, 1 failed`：`tests/integration/test_task015_p1_fix.py::test_valid_scoring_artifact_is_reused_without_calling_provider` 直接调用已禁止的 legacy `complete_stage(TRANSCRIPT_READY -> SCORED)`，报 `IntegrityConflict: TRANSCRIPT_READY -> SCORED requires the runtime trusted persistence entry`。该文件不在本任务允许范围，未修改。 |
| `.venv/bin/mypy tests/integration/test_state_store.py` | NOT GATING | 未作为任务要求的项目配置检查；直接按单文件运行时，installed `youtube_intel` 缺少 `py.typed`，报 `Skipping analyzing \"youtube_intel\"`，另有既有/fixture `type: ignore` 被判 unused。未改动测试配置或类型门禁。 |
| `git diff --check` | PASS | 无 whitespace error。 |

## Diff 复核

- 修改文件：`tests/integration/test_state_store.py`、本 handoff。
- 是否存在任务范围外修改：否；state-store 中仅移除了 legacy manual `SCORED` 状态推进，并添加 trusted integration fixture/test coverage。
- 是否存在生成文件或格式化噪声：否。
- 是否触及依赖、Schema、密钥、真实 Vault、云调用或调度红线：否；所有 transports 为 injected offline fakes，Vault 为 pytest temporary directory。

## 失败、跳过与风险

- 已解决失败：原 state-store suite 的两个 legacy scoring-completion failures 已替换，suite 从 `32 passed, 2 failed` 到 `36 passed`。
- 跳过检查及原因：无任务要求的检查被跳过；上述单文件 mypy 命令不是项目配置的门禁，结果已保留为 non-gating 环境问题。
- 剩余风险：全量 pytest 的唯一 blocker 位于范围外的 TASK-015 legacy-cache integration test；其迁移需要单独授权，不能由本任务修改。
- `DECISION NEEDED`：是否分配后续迁移任务处理 `tests/integration/test_task015_p1_fix.py` 的 legacy scoring completion fixture。

## 实现者结论

- 建议状态：`IN_REVIEW`
- Commit SHA：`7187fa8`
- 复现/验证说明：在本 worktree 使用 `.venv/bin/pytest` 运行以上命令；无网络、真实模型或真实 Vault 调用。
