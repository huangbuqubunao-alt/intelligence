# TASK-016C Phase E Implementer Authorization

## 身份与固定基线

你是 Implementer。仅实施 [TASK-016C Phase E](../tasks/TASK-016C-PHASE-E-trusted-scoring-finalizer.md)。
基线必须是本授权 control-plane commit；其唯一 Phase D 祖先为
`2c11faf41e17c3b823a39bfd1018c5c876b236c5`。先验证 branch、HEAD、父链与 worktree 洁净度。

先完整阅读 `AGENTS.md`、`docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、
`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`、ADR-025、ADR-026、
`docs/TASK-016C-PHASE-E-AUTHORITY-AMENDMENT-ROUND-3.md`、任务卡和 handoff。冲突即停止。

## 目标

实现 Round 3 已冻结的 four-part boundary：

1. `build_scoring_request_identity()` 是唯一 canonical、pure、legacy-compatible request identity builder；
2. `RuntimeOperations` 由 validated `AppConfig` 私有 mint opaque `TrustedScoringContext`；
3. 仅 `TrustedScoringFinalizer` 可 mint non-Pydantic opaque `TrustedScoreResult`；
4. Finalizer 重建所有不可信 DTO，先验证两个 authority，再重建 identity、验证 scoring provenance 与
   Phase D attestation，最后产生 wrapper；任何失败 fail-closed。

## 强制范围

只允许任务卡列出的文件。`scoring.py` 仅可抽取 identity；不得改变 ProviderCall schema、state hash
primitive、持久化、provider 行为或 cache。`quality.py` 不读取 config/settings/Mapping authority。
不得启动任何真实网络、Ollama、模型、Vault、DB、Artifact、cache 或 ProviderCall workflow。

## TDD 与交付

每个行为遵循一条 RED → 最小 GREEN：先 identity equivalence，再 context capability，再 result wrapper，
再 Finalizer positive/bypass matrix。测试必须走公开 revalidation 与 runtime composition path，不得以
private constructor 伪造成功 authority。完整门禁通过后检查 diff、敏感信息和禁止路径；追加
`handoffs/TASK-016C.md`，创建一个 implementation commit 后立即停止。禁止 review 自己、merge、push、
tag、rebase、squash、amend、启动 Phase F。
