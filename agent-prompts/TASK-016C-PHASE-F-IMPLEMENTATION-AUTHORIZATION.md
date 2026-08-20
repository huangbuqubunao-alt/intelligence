# TASK-016C Phase F Implementation Authorization

**状态：** `READY / AUTHORIZED`
**任务：** TASK-016C Phase F — PRIMARY In-Memory Trusted Scoring Seam
**角色：** WorkBuddy Implementer
**授权类型：** 控制面授权；本文件不启动实现。

## 已接受基线与历史

| 权威 | 提交 |
| --- | --- |
| 已接受 Phase D | `2c11faf41e17c3b823a39bfd1018c5c876b236c5` |
| 已接受 Phase E | `9b92946a3c156a7c365d808f92f7a1734dcca874` |
| 已接受 Phase F Round 4 设计 | `e00f9579bed3ad91a088c7f9a378cb0808308045` |
| 本授权控制面 | 本提交 |

Phase F implementation commit 必须是本授权提交的 descendant，并保留以上历史。禁止 squash、rebase、reset、amend 或 rewrite history。实现前必须核验所有 SHA、单父链和工作树；任一不符立即停止。

## 目标与唯一成功流

实现一个非生产、PRIMARY-only、纯内存 trusted scoring seam：

```text
ScoringInput
→ Ollama transport/parser
→ PrimaryScoringAttempt
→ ScoringCandidate
→ schema → TASK-016B language validation → quality gate/Judge
→ QualityPassAttestation → TrustedScoringFinalizer
→ TrustedScoreResult → PhaseFTrustedScoringSuccess
```

任一节点失败均 fail-closed。Phase F 不做 persisted runtime cutover；G 才拥有 `PREWRITE_VALIDATE`、持久化与正式切换，H 拥有 repair/retry/budget/recovery，I 拥有 cache verification/recovery 与 release acceptance。

## 冻结合同

### Provider 与 raw/candidate 边界

- trusted path 的 Provider 仅返回 `PrimaryScoringAttempt`，其唯一业务 DTO 是 `ScoringCandidate`；不得把 `ScoreResult` 当作 trusted output。
- `final_raw_response` 是完整、bounded、strict-UTF-8 decoded 的 Provider HTTP response body；禁止使用 `payload["response"]`、截断值、重新序列化 JSON 或替代 raw 表示。
- `raw_response_hash = SHA-256(final_raw_response.encode("utf-8"))`，对应 received exact response-body bytes。
- 只允许一个 pure canonical candidate parser：`raw → UTF-8 → JSON → parser → ScoringCandidate → build_scoring_candidate_hash()`。F 与未来 G 必须复用它；不得复制 parser 或 candidate-hash 算法。
- 创建 attempt 前必须验证 raw 上限/UTF-8、计算 raw hash、重 parse raw、重建 candidate/hash，并核对 supplied/returned candidate、request identity 和 provider/model/digest identity。`raw A + candidate B` 必须 fail-closed。

### Phase F success 与隔离

唯一成功输出是 `PhaseFTrustedScoringSuccess(trusted_result, primary_attempt)`，并 sealed：

- `scoring_request_hash`；
- `candidate_hash`；
- `raw_response_hash`。

其中仅 `TrustedScoreResult` 是 trusted business result；`PrimaryScoringAttempt` 始终是 PRIMARY-only、memory-only 的 untrusted continuation。aggregate 只是生命周期 handoff，不能成为 authority capability、Artifact、cache、ProviderCall、`response_artifact_id` 或 persistent record。

`RuntimeOperations → RepositoryBackedScoringService → ScoreResult → persistence` 仍是 `PRE-TASK-016C COMPATIBILITY PATH`。bare `ScoreResult`、legacy output/raw、Mapping 和 JSON 必须被新 seam exact-type 拒绝，且不得升级为 trusted continuation/result。

## 允许路径

最小实现范围仅限：

- `src/youtube_intel/providers/ollama.py`（只抽取/复用 pure parser 与 candidate/raw contract）
- `src/youtube_intel/scoring.py`（纯内存 seam 与 legacy isolation）
- `src/youtube_intel/runtime.py`（仅 composition wiring）
- `src/youtube_intel/quality.py`（必要的 Finalizer glue）
- `src/youtube_intel/domain.py`（必要 contract）
- 对应 focused unit/integration tests
- `handoffs/TASK-016C.md`

任何其他生产路径都需要 `DECISION NEEDED`，不得自行扩大范围。

## 禁止范围

禁止 `state.py`、DB schema/migration、Artifact 或 cache persistence/recovery、ProviderCall completion/persistence、filesystem commit protocol、repair/retry/budget/recovery、Phase G+、依赖或 `uv.lock`。禁止真实 Ollama、network、cloud、Vault、凭据或 fallback。

不得改变 transport behavior、loopback guard、model selection、download/fallback/network semantics、TASK-016B Language Validator、默认 persisted runtime dispatch。不得创建 TrustedScoreResult/attestation 的 provider 侧捷径。

## TDD 与对抗验收

先 RED 后最小 GREEN，并记录两者证据。至少覆盖：

1. Provider trusted path 产生 Candidate/Attempt，而非 `ScoreResult`；candidate 业务字段兼容。
2. exact bounded raw 保持在内存；oversized raw 或 invalid UTF-8 fail-closed。
3. 一 byte raw mutation 改变 raw hash；语义相同而 bytes 不同的 JSON 具有不同 raw hash。
4. raw/candidate mutation、provider/model/request mismatch、非 PRIMARY role 均被拒绝。
5. 合法 PRIMARY 流到达 `TrustedScoreResult`；language、quality 或 attestation 失败均阻止成功 aggregate。
6. bare `ScoreResult` 与 legacy output 不能升级。
7. 不调用 `RepositoryBackedScoringService` persistence path，且零 Artifact/cache/ProviderCall/DB/filesystem/stage/response-ID 副作用、零 repair/retry。
8. Phase C/D/E trust tests 与 TASK-016B ordering 保持 green。

Mutation proof 必须证明删除 raw reparse、raw-hash comparison、candidate-hash comparison、exact-type trusted-result guard 或 legacy isolation guard 会使测试失败；所有 mutation 必须在提交前恢复。

## 必须门禁

```text
uv lock --check --offline
uv sync --locked --offline
focused Phase F tests
existing Phase A–E focused trust tests
uv run pytest -x -q
uv run mypy src
uv run ruff check .
uv build --offline
bash scripts/security_scan.sh
git diff --check
```

不得下载、联网或调用真实模型。最终必须复核 Diff 仅包含授权路径。

## 提交、回滚与交接

全部门禁通过后，仅创建一个可独立 revert 的 implementation commit：

```text
TASK-016C Phase F implement primary in-memory trusted scoring seam
```

追加 `handoffs/TASK-016C.md`：父/实现 SHA、精确路径、RED/GREEN、mutation、raw/candidate binding、零持久化、legacy isolation、门禁、复用决策、偏差、跳过项和风险。提交后停止，等待独立审查；不得 merge、push、tag 或进入 G。
