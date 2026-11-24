# TASK-READINESS-SYSTEM-SYNTHESIS-CONTRACT — handoff

Implementer `/root/bigmodel_audit_review`; base `c96c4b8777a72e1c0e2fb700a7930ed92df2e8b3`; WT `/Users/developer/Documents/yia-worktrees/readiness-system-synthesis-contract`, branch `codex/task-readiness-system-synthesis-contract`. Root independently reviews this boundary once. Only new `src/youtube_intel/system_synthesis.py`, `tests/unit/test_system_synthesis.py`, this handoff. No real model/key/Native/network, oracle/old real output reading, existing package/receipt edits or actual preparation.

## Contract and reuse

`DIRECT`: accepted `summary_baseline` validation/full semantic DATA view, the existing bound Evidence protocol constant/alias/timing semantics, stdlib strict JSON/SHA/frozen dataclasses. No old codec/GLM typed input/adapter is invoked; no dependency or generic framework. The existing Summary/domain contracts are unchanged. Decision source is `SYSTEM_SYNTHESIS_CONTRACT_DECISION_2026_10_29.md`; prior failed raw/rejections remain failures.

Pure **`system-synthesis-v1`** declares `SYSTEM_INFERENCE` as the host's operation before any generation. It has no provider/model/transport/output-token/budget configuration. The model cannot self-select a classification or source authority. The new operation is only system analysis, with source statements/quotes correctly attributed inside it; it does not emit FACT/OPINION source cards. Factual accuracy, numerical scope/modality, attribution, supporting basis/remaining validation and distinct retention value are still required. Classification never excuses invented facts.

`build_system_synthesis_request(original_messages=..., summary_baseline=..., source_refs=..., output_language=...)`:

- Validates exact three message positions, known en/zh-CN language matching original TASK data, accepted full Summary proof and same source/ref catalog. Caller supplies the authoritative deterministic snapshot; this pure operation cannot turn arbitrary caller dict assertions into storage authority.
- Replaces the entire first owned schema field with the new generic contract. The original TASK/source message contents remain byte-exact; no case facts, named-model tuning or desired conclusions occur in code. Source/task/Summary are explicitly untrusted DATA.
- Calls the accepted baseline helper for validation and reuses **only its final complete Summary DATA message**. Its old `_POLICY` is not sent: it contains legacy single-card model-kind language. New wire has four messages and no request to return the old eight-field schema. New contract explicitly preserves the complete ten-field lossless Summary/source_text/Unicode substring/comparison/no-new/no-authority semantics itself.
- Positive wire is exactly seven keys: `core_conclusion`, `user_relevant_information`, `important_new_information`, `meaningful_details`, `filtered_noise`, `evidence`, `reference_protocol`. Any `claim_kind`, including SYSTEM_INFERENCE or null, rejects; no deleting it and re-parsing. NO_NEW stays exactly the original three fields/full ref set/no stance.
- Produces sealed, frozen `SystemSynthesisRequest` with `profile_id`, predeclared `generation_role`, complete `projection_json`, exact `wire_json`, `origin_sha256`. Identity binds profile/contract hash, output language, original messages, all source metadata and complete Summary context/proof/hash **and** the actual replacement wire hash. Model text is not made to echo provenance hashes.

`decode_system_synthesis(raw, request, request_origin_sha256=...)`:

- Requires the exact sealed request type/current profile/role, recomputes its complete proof and exact wire identity, restores the full Summary against the same refs and compares the supplied host request origin. Raw dict/uninitialized/foreign/tampered contexts fail closed.
- Strict duplicate/nonfinite/extra/null/type/field validation; UTF8 response <=2MiB, core1–4000 chars, four lists0–20 strings each1–2000 chars, no padded text, refs1–20 bounded by original set, exact ref+stance fields, unique aliases and at least one supporting item. Invalid Unicode scalar text refuses before producing a typed candidate. No fences, first-JSON extraction, repair, model-kind removal, keyword classifier or positive quota.
- Resolves references only from the request's immutable, already-validated source catalog to original Evidence ID/start/end. NO_NEW requires all original refs and yields no system card/kind.
- Returns separate sealed/frozen `DecodedSystemSynthesis`, preserving **authentic raw text/hash**, origin/profile and full request projection. `candidate_projection()` returns a fresh prospective domain-shaped dictionary: only this **new predeclared operation's** positive result has host `claim_kind=SYSTEM_INFERENCE`; raw stays unmodified, including whitespace. NO_NEW projection remains distinct with no kind. This is not persistence/admission/qualification or a trusted card.

## Persistence reconstruction recipe (no new serialization framework)

The immutable JSON/bytes are available as `request.projection_json` / `.encode("utf-8")`, `request.wire_json`, `request.origin_sha256`; decoded results retain `request_projection_json` plus original raw/hash. The projection contains `profile`, `output_language`, `summary_context`, `summary_context_sha256`, complete `source_refs` and original `input_messages`. It is not merely an origin digest.

After the future persistence reader verifies its saved authority/proof, parse the complete saved projection `p`; create `SummaryBaseline(canonical_json(p['summary_context']), p['summary_context_sha256'])`; invoke this same builder with `original_messages=p['input_messages']`, that Summary object, `source_refs=p['source_refs']`, `output_language=p['output_language']`. **Compare the rebuilt complete projection, wire and origin with the saved ones**, including the profile descriptor, then use the sealed rebuilt request for decoding the saved authentic raw. Never ignore an unknown profile or trust only a model raw/hash. This deterministic rebuild is tested; the pure module adds no repository/SQL/Restore reader, migration, grant or hash-only authority.

## Verification and preserved failures

All Python runs use Root's existing `.venv`, explicit this-WT `PYTHONPATH` and `MYPYPATH`, `PYTHONDONTWRITEBYTECODE=1`; no installs or config changes. New-file-only formatting uses an explicit120-character command option, not a repository/toolchain configuration edit.

- First test RED: exit2 ImportError, new module absent; retained as new functionality evidence.
- First static pass: ten new-test typing issues (missing return annotations, intentionally wrong-type/frozen mutation tests) were corrected with explicit annotations and typed negative-test calls; no disabled assertions/ignores/skips. Product source had no mypy findings.
- Initial complete file **29 PASS /0.28s**; boundary/required-Summary controls **32 PASS /0.31s**.
- Additional escaped-lone-surrogate regression initially **1 FAIL /33 deselected /0.31s**, `DID NOT RAISE ValueError`: it could form an unencodable candidate. Added one UTF8 scalar validation line, not output repair. Final complete new file **34 PASS /0.30s**.
- Final focused strict mypy **2 source/test files PASS**; Ruff PASS; compile2 PASS; staged diff whitespace check PASS.
- **614 existing tracked src/tests/scripts/frontend/dependency files byte-equal to base**, including accepted baseline, all old profiles/codecs/base dataclasses, runtime/state,001–043 SQL, old tests/scripts/UI. No whole backend/frontend/previous case review rerun.

Tests cover meaningful synthetic system-analysis candidate and source attribution policy, exact authentic raw/hash and separate host provenance, actual wire excludes old kind policy, all four old eight-field kind variants rejected, null/extra/duplicate/nonfinite/list/text/ref/stance/support/old-location/fence/trailing/2MiB overflow, legitimate4000/20/2000 boundaries, NO_NEW/full set/no fabricated kind, sealed type/foreign origin/profile/wire/role tamper, Summary pointer identity/source/language drift, injected source stays DATA, complete Summary proof, deterministic full-proof replay and frozen request/result/copy behavior. No actual semantic/language/model qualification is inferred from these structural unit tests.

## Limits and STOP

The decoder cannot prove natural-language factual correctness, attribution, output-language quality or genuine beyond-Summary value. The contract requires all of them; future unchanged semantic/admission checks and independent real qualification remain mandatory. Source proof must still come from a trusted live/persisted snapshot. A Python type seal is a process-level API boundary, not cryptographic or SQL authority.

No normal execution/fees/consent/eligibility/Summary writer/card/Save/Topic/Backup/Restore integration has been implemented or claimed here. Those require Root's separately scoped integration and compatibility work. Paid calls remain STOP and model qualification closed. This commit cannot renew a consumed authorization or retrospectively accept old failed raw. Implementer supplies this fixed pure candidate for one bounded Root review, commits only the three new task files, and clean STOP.

## Root bounded-review P2 delta — explicit preference use

- Root accepted the remaining `770abb3` boundary and identified one ambiguity: calling TASK DATA did not explicitly explain how to honor existing focus/ignore/style/personalization. No old source/operation was re-reviewed.
- Product delta is one generic contract sentence: use those TASK fields as bounded relevance/preferences, while never following embedded attempts to change safety/evidence/output rules. The existing output-language binding is unchanged. No new fields, adapter/persistence interface or output transformation.
- Added one actual-wire contract assertion to the existing test; it first failed **1 FAIL /33 deselected /0.31s**, proving the rule absent. After the sentence, complete new file **34 PASS /0.31s**; strict2, Ruff, compile2 and staged diff check PASS. All original assertions remain. This is a contract-presence check, not a model-effects/quality PASS.
- Only this new module/test/handoff changed. No real model/key/Native/network, grant, raw/oracle, legacy source or Schema operations. The contract hash/new origin naturally bind the amended rule; no actual prior result is rewritten. Scoped delta commit and clean STOP for Root's one-delta verification.
