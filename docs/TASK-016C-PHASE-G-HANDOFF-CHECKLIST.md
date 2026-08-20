# TASK-016C Phase G Independent Review Checklist

## 固定对象与 Git 门禁

- [ ] 实现 commit 是 `bff2b7d…` 的单父 descendant；D/E 与 F equivalence chain `61bb0bb… -> d059bea… -> 2f6e30b…` 均为 ancestor。
- [ ] 仅一笔 Phase G implementation commit；无 merge/rebase/squash/amend/history rewrite。
- [ ] Diff 只涉及 authorization allowlist；无 `providers/ollama.py`、`domain.py`、TASK-016B、Cloud、Router、Weekly、migration、dependency 或 lockfile。
- [ ] `git diff --check`、worktree status、敏感形状扫描均通过。

## Trusted ingress 与 PREWRITE_VALIDATE

- [ ] 只接受 exact `PhaseFTrustedScoringSuccess`；bare/single/Mapping/JSON/cache/Artifact/ProviderCall/legacy material 都 fail-closed。
- [ ] success 封存 canonical ScoringInput、quality input/full PASS result/operation/attestation、sealed structured-result bytes/hashes；缺失或篡改不可由 caller DTO 补入。
- [ ] exact raw hash、same parser、candidate hash、candidate/result binding、request identity、provider/model/digest/schema/prompt/operation/output language、current runtime authorities、attestation/H2 和 config rotation 全部在写前重验。
- [ ] structured bytes 只经 sealed serializer；无 G-facing bare `ScoreResult` unwrap。
- [ ] PREWRITE 失败时不存在 tmp/final/mkdir/Artifact/ProviderCall/cache/SQLite/stage/response_artifact_id。

## File、DB、runtime 与 legacy

- [ ] raw source 唯一为 `primary_attempt.final_raw_response`；无 recall、payload extraction、cache/Artifact/caller/legacy substitution、provider JSON reserialization。
- [ ] writer 顺序为 tmp exclusive create → fsync → hash/length → no-clobber promote → dir fsync → final reopen verify；path/symlink/cross-device/existing conflict fail-closed。
- [ ] two files verify 后，单一 transaction 原子登记两 Artifact、transient PENDING→SUCCEEDED scoring/Judge ProviderCalls、scoring summary/stage/job；无 prewrite reservation。
- [ ] DB failure 不删除/覆盖 promoted finals；只留 H 可判定 orphan state；不实现 recovery。
- [ ] normal `RuntimeOperations.scoring_stage` 仅走 trusted route；legacy route 仅 compatibility，不可升级为 trusted input；G 不读/返回 cache hit。
- [ ] duplicate only succeeds after exact complete graph equality；PENDING/FAILED/partial/legacy conflict fail-closed。

## 证据

- [ ] RED-first、adversarial matrix、M1–M10 mutation evidence 完整且恢复后 GREEN。
- [ ] focused G、Phase F、A–E trust、TASK-016B、full pytest、mypy、Ruff、offline build、security scan 与 diff check 独立复跑通过。
- [ ] 无真实 Ollama/network/Cloud/Vault/credential/repair/retry/recovery/cache-hardening 操作。
- [ ] handoff 记录准确，不把 Phase G 实现写成 review approval、merge 或 release。

Reviewer 只能记录 evidence；发现 P0/P1 应立即停止，不得自行修复或合并。
