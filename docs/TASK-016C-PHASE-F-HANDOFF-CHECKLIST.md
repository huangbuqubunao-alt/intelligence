# TASK-016C Phase F Handoff and Independent Review Checklist

**状态：** `READY / AUTHORIZED`
**Review target：** 一个且仅一个 implementation commit，必须为 Phase F authorization、Phase E `9b92946…` 与 Phase D `2c11faf…` 的 descendant。

## Implementer Completion Record

- [ ] 已验证 ancestry、工作树和单一 implementation commit；未 squash/rebase/rewrite。
- [ ] 仅修改授权路径；未触及 `state.py`、DB、migration、Artifact/cache persistence、ProviderCall completion、filesystem protocol、repair/retry、依赖或 lockfile。
- [ ] Provider trusted path 只返回 parser-derived `ScoringCandidate`/`PrimaryScoringAttempt`，未返回/升级 `ScoreResult`。
- [ ] `final_raw_response` 是 exact bounded strict-UTF-8 decoded HTTP body，且 `raw_response_hash` 为其 UTF-8 bytes 的 SHA-256。
- [ ] F 与未来 G 共用同一 pure canonical parser；raw→candidate→candidate-hash 链已建立。
- [ ] Attempt 绑定 request/candidate/raw hash、provider/model/digest 和 `PRIMARY`；`raw A + candidate B` fail-closed。
- [ ] `PhaseFTrustedScoringSuccess` 仅配对 `TrustedScoreResult` 与 untrusted attempt，并 sealed 三个 identity hash。
- [ ] legacy/bare `ScoreResult`、legacy raw、Mapping、JSON 均不能进入或升级 trusted seam。
- [ ] 已记录 RED、GREEN 和五项 required mutation evidence。
- [ ] 已确认 F 无 Artifact/cache/ProviderCall/DB/filesystem/stage/response-ID side effect，且无 repair/retry。

## Mandatory Gate Evidence

- [ ] `uv lock --check --offline`
- [ ] `uv sync --locked --offline`
- [ ] focused Phase F tests
- [ ] existing Phase A–E focused trust tests
- [ ] `uv run pytest -x -q`
- [ ] `uv run mypy src`
- [ ] `uv run ruff check .`
- [ ] `uv build --offline`
- [ ] `bash scripts/security_scan.sh`
- [ ] `git diff --check`

## Independent Reviewer Acceptance Matrix

- [ ] 一个 raw byte mutation、equivalent reserialized JSON、oversized raw、invalid UTF-8 均按 frozen contract 处理。
- [ ] Provider/caller 无法提供 independent candidate 或让 raw A + candidate B 通过；candidate mutation、provider/model/request identity mismatch、非 PRIMARY role 均 fail-closed。
- [ ] Phase F 只在有效 schema/language/quality/attestation 下输出 `TrustedScoreResult` 和 aggregate；任何失败均无 success aggregate。
- [ ] aggregate 和 `TrustedScoreResult` exact-type/private-sentinel 防止 bare result、Mapping、JSON、legacy output upgrade。
- [ ] F 不实例化/调用 `RepositoryBackedScoringService` persistence execution path，不完成 ProviderCall，不产生 Artifact/cache 或写入。
- [ ] raw reparse、raw hash compare、candidate hash compare、trusted-result exact-type guard、legacy isolation guard 的 mutation removal 均被测试捕获。
- [ ] 现有 Phase C/D/E trust tests、TASK-016B ordering 和 full gates 均无回归。
- [ ] Diff 范围、无新增依赖/lockfile、`git diff --check` 和 handoff 证据均符合要求。

## 必须交接内容

Handoff 必须包含 implementation SHA/parent、精确文件清单、RED/GREEN、所有门禁、对抗与 mutation cases、raw/candidate binding、零持久化与 legacy isolation 证据、reuse decision、未执行禁止动作和剩余风险。独立 verdict 只能为 APPROVE 或 REJECT；它不授权 merge 或 Phase G。
