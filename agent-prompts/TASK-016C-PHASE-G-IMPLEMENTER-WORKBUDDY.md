# TASK-016C Phase G — WorkBuddy Implementer Prompt

你只实现已授权的 Phase G，不是 Reviewer 或 Integrator。开始前完整阅读：

1. `docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`；
2. `docs/decisions/ADR-025-content-quality-layer-scope-boundary.md`；
3. `docs/TASK-016C-PHASE-G-PREWRITE-PERSISTENCE-RUNTIME-CUTOVER-AMENDMENT.md`；
4. `agent-prompts/TASK-016C-PHASE-G-IMPLEMENTATION-AUTHORIZATION.md`；
5. interface、test plan 与 `handoffs/TASK-016C.md`。

## 入口与停止条件

- 基线必须为 `bff2b7d514ce4d65f5a2b68d976c5085539e728d` 的 descendant，且 Phase D/E 与 integrated Phase F equivalents `61bb0bb… -> d059bea… -> 2f6e30b…` 都是 ancestor。
- tracked worktree 必须 clean；若发现 source/authorization/设计冲突、缺依赖、范围外修改、真实网络要求或 migration 需求，立即停止并报告 `DECISION NEEDED`。
- 只创建一个 implementation commit：`TASK-016C Phase G implement trusted prewrite persistence cutover`。
- 禁止 merge/rebase/squash/amend/push/tag/release；完成后等待独立 Reviewer。

## 必须实现

```text
exact PhaseFTrustedScoringSuccess
-> PREWRITE_VALIDATE (zero writes)
-> opaque ValidatedScoringWritePlan
-> verified tmp/fsync/no-clobber promote/final verify
-> one SQLite transaction (Artifact + scoring/Judge calls + scoring stage)
-> normal RuntimeOperations cutover
```

必须最小 enrich 同一 success aggregate，封存 canonical scoring and complete quality evidence；不能以 caller Mapping/JSON/DTO 补信任。对 `TrustedScoreResult` 只能经 sealed serializer 获得 structured bytes，不可向 G 调用方 unwrap bare `ScoreResult`。raw source 只能是 exact `primary_attempt.final_raw_response`，必须复用 Phase F canonical parser 重新验证。

前置验证失败必须无任何 filesystem/SQLite/Artifact/ProviderCall/cache/stage effect；不得 reserve。normal runtime scoring stage 必须只走 trusted primary seam + committer，legacy service 不得作为 normal producer。G 不做 repair/retry/recovery/cache hit/recovery，也不调用真实 provider/Judge。

## 允许/禁止文件

仅可修改 `src/youtube_intel/scoring.py`、`runtime.py`、`state.py`、必要时 `quality.py`，以及 authorization 列出的 Phase G/Phase F/quality/scoring/runtime/operations tests 与 `handoffs/TASK-016C.md`。禁止 `providers/ollama.py`、`domain.py`、TASK-016B、Cloud/Router/Weekly、schema/migration、dependency/lockfile；不足时停止。

## TDD、验证与交接

严格 RED → minimum GREEN。完整执行 authorization 中的 adversarial matrix、M1–M10 mutation proof 和所有 offline gates。使用 Fakes/temporary SQLite/DATA roots 证明 normal commit、zero-write-before-prewrite、raw/candidate/result/authority attacks、no recall、two-call atomic DB registration、file/DB failures、legacy isolation、idempotency 和 normal runtime cutover。

在 `handoffs/TASK-016C.md` 记录 direct parent/SHA、文件范围、RED/GREEN/mutation/gates、无真实网络、未实施 H/I 与任何 P2。不要自称 APPROVED，也不要进入 review/merge。
