# TASK-016C Phase F — WorkBuddy Implementer Prompt

## 角色与停止边界

你是 TASK-016C Phase F 的 WorkBuddy Implementer。只实现 PRIMARY-only、candidate-only、memory-only 的 trusted scoring seam，创建一个 implementation commit 后停止等待独立审查。禁止 merge、push、tag、rebase、squash、reset、amend、history rewrite，以及启动 Phase G–I。

## 开始前必读与 Git 门禁

按顺序阅读：

1. `docs/COLLABORATION.md`、`docs/PROJECT_STATUS.md`、`docs/PRD.md`、`docs/SYSTEM_DESIGN.md`、`docs/REUSE_REGISTER.md`
2. `docs/decisions/ADR-025-content-quality-layer-scope-boundary.md`
3. `docs/TASK-016C-PHASE-F-RUNTIME-INTEGRATION-AMENDMENT.md`
4. `docs/TASK-016C-CONTENT-QUALITY-INTERFACE-DESIGN.md`
5. `docs/TASK-016C-CONTENT-QUALITY-TEST-PLAN.md`
6. `docs/TASK-016C-IMPLEMENTATION-MASTER-PLAN.md`
7. `handoffs/TASK-016C.md`
8. `agent-prompts/TASK-016C-PHASE-F-IMPLEMENTATION-AUTHORIZATION.md`

核验 accepted design `e00f9579bed3ad91a088c7f9a378cb0808308045`、Phase D `2c11faf…`、Phase E `9b92946…` 都是当前分支祖先，且当前分支包含 Phase F authorization commit。工作树或授权链不符即停止报告；不得以 rebase/squash 修复。

## 实施目标

让 PRIMARY provider flow 形成：

```text
exact bounded raw HTTP body
→ same pure canonical candidate parser
→ parser-derived ScoringCandidate + candidate hash
→ schema/language/quality/attestation/finalizer
→ TrustedScoreResult
→ PhaseFTrustedScoringSuccess
```

`raw_response_hash = SHA-256(final_raw_response.encode("utf-8"))`。F success 必须 seal request/candidate/raw hashes；任何 mismatch、裸/legacy `ScoreResult`、Mapping、JSON、非 PRIMARY role 或失败 quality/attestation 都 fail-closed。

## 允许路径与禁止工作

仅按 authorization 中的 allowed paths 最小修改。`providers/ollama.py` 只可抽取或复用 pure parser/attempt contract；不得改变 transport、loopback、model、download、fallback 或 network semantics。`scoring.py` 只实现无副作用 seam；`runtime.py` 只作 composition wiring。

禁止 `state.py`、DB/migration、Artifact/cache、ProviderCall completion、filesystem protocol、repair/retry/budget/recovery、默认 persisted dispatch、TASK-016B Language Validator、依赖/lockfile、真实 Ollama/network/cloud/Vault。需要任何未授权路径立即输出 `DECISION NEEDED`。

## 强制 TDD 与对抗证明

先添加 focused RED，再最小 GREEN。覆盖 Authorization 的全部 22 项，并特别证明：

- raw A + candidate B、candidate mutation、raw one-byte mutation、provider/model/request mismatch 均拒绝；
- canonical parser 只有一份，attempt candidate 只来自该 parser；
- valid PRIMARY 到达 wrapper，而 language/quality/attestation failure 无 result/aggregate；
- 纯内存 seam 不调用 legacy persistence service，也无任何写入或 repair/retry；
- bare/legacy `ScoreResult` 不可升级。

临时删除 raw reparse、raw-hash comparison、candidate-hash comparison、trusted exact-type guard 与 legacy isolation guard，记录对应 tests 失败；每次均恢复后继续。

## 验证、提交与停止

依次运行 authorization 指定的 offline/full gates。门禁失败不得弱化测试或重试真实 Provider。最终确认仅允许路径、`git diff --check` 通过且工作树没有无关变更。

创建唯一提交：

```text
TASK-016C Phase F implement primary in-memory trusted scoring seam
```

在 handoff 记录完整 TDD、mutation、binding、零副作用、legacy isolation、gates、reuse、风险与父 SHA。停止，不自行审查、合并或继续 Phase G。
