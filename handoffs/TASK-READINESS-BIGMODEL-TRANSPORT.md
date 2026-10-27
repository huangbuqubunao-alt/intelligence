# TASK-READINESS-BIGMODEL-TRANSPORT — implementation handoff

- Role: Implementer `/root/cloud_preview_writer`, sole writer, no subagents.
- Base: `523bff80d343949f57159b94e10ed1c4328144e5`.
- Worktree: `/Users/hua/Documents/yia-worktrees/readiness-bigmodel-transport`.
- Branch: `codex/task-readiness-bigmodel-transport`.
- Fixed author commit: reported with this handoff in the final chat; independent review/integration belongs to Root.

## Scope and frozen profile

Only `distillation.py`, two new offline test files and this handoff change. No SQL/schema, state repository, runtime composition, API/DTO, UI, settings, credentials/configuration, budget policy, dependencies/lockfiles, owner data, Root QA services or main changes. Normal production eligibility remains false; current production spending policy still denies unconfigured cloud. No provider API request, authenticated operation, model generation, account registration or fee occurred.

`BigModelGlm47FlashDistillationTransport` is a distinct qualification-only `zhipu_bigmodel` / `glm-4.7-flash` adapter. Endpoint is exactly `https://open.bigmodel.cn/api/paas/v4/chat/completions`; nonstreaming, `thinking.type=enabled`, `response_format.type=json_object`, `max_tokens=16384`, `temperature=1.0`, timeout300 seconds, retries0. Request profile is `bigmodel-glm-4.7-flash-thinking-json-qualification-v1`; common prompt remains `m12-intelligence-admission-v1`. Both existing system messages and user Evidence message retain exact text/order, including source/task/personalization separation, both languages and every supplied Evidence item. No prompt transform or evidence truncation. Input limit128KiB serialized UTF-8 is a transport ceiling, not a tokenizer/context-capacity claim; response limit2MiB.

All frozen parameters/bounds participate in the new pair's verified semantic hash; profile version also participates in canonical reservation ID. Existing provider hashes/profile IDs/wire builders remain unchanged. Source identity uses existing sealed Evidence/source-policy verification; LOCAL, BILIBILI and local-content-shaped IDs cannot reach this wire. `CLOUD_PROVIDERS`/`ZHIPU_PAIR` reuse the accepted finite audit descriptor, not an eligibility grant.

Pure `_request` and existing `_cloud_request_preview` work without credential resolution or writes. New-provider consent/review lookup uses existing042 receipt routing. Owner qualification uses `continue_qualification_reserved_distillation` → current Evidence/policy/budget/permit/consent checks (new-pair consent also precedes credential preflight) → existing durable claim → `_dispatch_and_admit` → existing decoder/admission/accounting. The old generic `distill` source-run entry now treats only this new pair as normal production, so it cannot borrow a qualification permit. Old adapters keep their prior behavior. No duplicate execution lifecycle or transport counter is introduced; durable once-only authority remains the existing service/repository claim.

## Official sources and reuse

Used agent-reach web/Jina read-only routing, not a provider API call. Rechecked official current pages on2026-10-27 and compared Root's cached2026-10-26 preflight sources:

- [GLM-4.7-Flash guide](https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash): exact model, thinking and temperature example; text/JSON support.
- [Chat completion API](https://docs.bigmodel.cn/api-reference/模型-api/对话补全): fixed endpoint, supported system/user messages, stream/max_tokens/response_format and response structure.
- [Official OpenAPI](https://docs.bigmodel.cn/openapi/openapi.json): `ChatCompletionResponse` has model/choices/usage, no required Moonshot `object`; `stop` means normal terminal result, and tool_calls/length/sensitive/network_error/model_context_window_exceeded are not accepted terminal finals here. Cache usage is nested under `usage.prompt_tokens_details.cached_tokens`. Generic schema labels some counts as number; this text-only adapter conservatively requires nonnegative JSON integers fitting SQLite int64, rejects booleans/floats, and checks totals/cache consistency when available.

Public read-only snapshots are ignored under `.var/bigmodel-transport/`: guide SHA256 `4f0f950d1fc0bd29ffbbd5b6c9d22e3ae4cfb4e7a92f8df009d7a6bdc8610434`, API `657d763f658dad3efaf2756634b74bf2c3559c68537de8c9fcef2513911e8307`, OpenAPI `d09b55b70a26fa6ea503f92b7ed85cc56f365cb5a37a479afc507e5f54a54ba4`.

DIRECT existing Python standard-library TLS/HTTP/JSON/time/threading and existing consent/claim/decoder/admission/accounting. ADAPT existing project cloud boundaries without changing old adapters. REFERENCE official protocol; no SDK or copied third-party implementation. Standard library PSF license and repository-owned implementation, no new dependency/license obligation. REJECT/DEFER arbitrary endpoints, redirects, retry/fallback, tools/media, new credential integrations, production grants and model qualification. Jev is not exposed; existing safe/default workflow retained.

## Wire and response safety

Standard verified TLS context, fixed host/path, bearer header only; no secret in request body/URL/projection/errors. Invalid/missing credentials fail before connection. Explicit TLS connect disables HTTPConnection auto-reconnect. A bounded connector waits only until the same absolute deadline; a platform DNS operation may finish later on its daemon thread, which can only establish/close TLS and never send HTTP. Deadline watchdog retains the original socket even after `Connection: close` detaches it, interrupts header/body reads, and cancels on exit. Per-read remaining-time checks cannot be extended by successful small reads. No redirect following, second POST or provider fallback.

A definite connect refusal is pre-dispatch and retains the original WAITING_MODEL/count0 terminal accounting, with no same-execution replay; after POST begins, timeout/reset/incomplete declared body/HTTP202 are ambiguous and cannot replay. HTTP401/429 have known independent042 failure receipts. Complete but malformed, missing/wrong identity, multiple choices, non-assistant/tool/media, non-stop/length/empty, invalid JSON/duplicate keys or invalid usage fail closed. Official response parsing does not assume Moonshot's object discriminator. Only exact model public final and named accounting fields escape; private reasoning and arbitrary response metadata are discarded. Internal raw response bytes have suppressed repr and are never logged or persisted. Absent usage/cost stays unknown; output token counts are service reported, not public-text token estimates. No current-price0 assertion becomes spending authority or a fabricated zero bill.

## Verification and failure evidence

All Python runs use Root's existing interpreter `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`, explicit `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=/Users/hua/Documents/yia-worktrees/readiness-bigmodel-transport/src`.

- Initial meaningful RED:36 new protocol tests failed because the candidate adapter was absent; then36PASS.
- New service RED: keyless preview refused the new pair before finite consent/profile/preview integration.
- Generic-entry counterfactual RED: restored only prior `normal_production=False` qualification behavior temporarily; the focused test failed at `source-run must not resolve credential`. Source was restored byte-identically immediately; no other test/source changes, DB/model or real credential involved.
- Intermediate77 focused tests passed before final extra boolean-call/known-connect assertions. A12-file affected regression follows; its exact final results and any repairs are recorded below, not replaced by that intermediate count.
- Initial strict mypy found one Optional comparison; fixed by narrowing the existing local variable. Ruff found compact new-test formatting/import order; only new tests were formatted, no assertion deleted/skipped/weakened.
- The first integration matrix expected the public usage reader to return None for a separate failure receipt. Existing reader correctly projects that receipt; stronger assertions now prove the physical resource table stays empty, independent failure receipt is exact, model/tokens/cost remain NULL, and status is retained. This was test expectation repair, no accounting product change.

Additional fixed-source repair evidence: the first12-file run completed **574PASS/1FAIL**,383.14s, one expected duplicate-ZIP fixture warning. Its sole failure was the new known-connect case: `generate` had wrapped `CloudDistillationPreDispatchError` into ambiguity. Preserving that exact known pre-dispatch exception fixes it without weakening unknown handling. Three additional real RED cases showed absent/wrong-hash/wrong-kind consent could resolve credentials via original preflight ordering; only the new pair now verifies that consent first. Focused repair4PASS, then final candidate82PASS20.10s. No old test assertion changed.

Final fixed-source checks:

| Check | Result |
|---|---|
| Focused new protocol/service tests |82PASS20.10s |
| Final complete12-file affected group |**578PASS**,387.37s; only expected duplicate-path ZIP fixture warning |
| Strict mypy all source, explicit task import path |122files PASS |
| In-memory compile all source, no bytecode writes |122files PASS |
| Ruff no-cache on changed source/new tests |PASS |
| AST source segments of10 old adapters/builders/parsers/shared prompt |Byte-identical to accepted523b base |
| All packaged SQL001–042 |41 files byte-identical to accepted base |
| Final group before/after hashes |165 source/SQL/new-test files unchanged |
| Full scoped diff and whitespace review |PASS; four allowed files only |

Reproduce the final affected group after the explicit environment/interpreter prefix above:

```text
-m pytest -p no:cacheprovider
 tests/unit/test_bigmodel_distillation_adapter.py
 tests/integration/test_bigmodel_distillation_transport.py
 tests/unit/test_moonshot_distillation_adapter.py
 tests/unit/test_openai_distillation_adapter.py
 tests/unit/test_distillation_dispatch.py
 tests/unit/test_bigmodel_claims.py
 tests/integration/test_task022_personalized_distillation.py
 tests/integration/test_task023b_distillation_reservation.py
 tests/integration/test_distillation_source_context.py
 tests/integration/test_local_intelligence_timed.py
 tests/integration/test_local_intelligence_text.py
 tests/unit/test_backup_restore.py -q --tb=short
```

The argument list above is one command (line breaks for readability). Full command, exit0, duration and all165 hashes are in ignored `.var/bigmodel-transport/final-affected.json`; stdout is `final-affected.log`. These totals overlap the focused run and are not additive. Log SHA256: `69a9387cb07d5a061ff039d8db0e6d3e419e8fc3a4f765b5bb83a0736f9f35c6`.

Coverage includes true zero-write keyless/repeated preview, frozen en/zh wire bytes, exact source/Evidence and profile changes, normal/generic route refusal, absent/mismatched consent before credentials, secret/reasoning projection denial, native fake-TLS/body/deadline/redirect/retry classifications, known no-HTTP failure versus unknown POST, schema/Evidence admission/NO_NEW, separate042 receipt accounting, concurrent claims, restart/no replay, SQL row and physical synthetic DATA preservation, old adapters/source reservation/privacy/local-text/timed and Backup/Restore regression. No tests/assertions skipped, removed or weakened. Whole-feature full regression and real API/GUI/model acceptance are intentionally later Root gates, not claimed by this slice.

## Limits and next gates

All positive responses, usage and account tokens in tests are explicitly synthetic offline fixtures. Public final schema/Evidence admission, NO_NEW, consent, claimed race, unknown outcome, restart and physical DATA preservation are engineering evidence only. Actual standard-library network reachability is untested; Root's old HEAD used a127.0.0.1 proxy and was not proof of this transport path. Root separately reports an unauthenticated/no-body standard-library HEAD401 at2026-10-27T07:57:19Z/0.118s; that is independent reachability-to-auth evidence only, not an author test or account/model proof. User reports registration complete and no recharge; no key was supplied to this author. Account entitlement, current free policy, quota/privacy acceptance, actual usage/bill and semantic quality remain unverified. No credential namespace is installed or read here. Root owns later isolated provider-specific settings, finite free-policy authorization, frozen public-sample real qualification, actual GUI/full feature regression/backup and adoption. This slice does not qualify GLM or declare the ordinary-user Goal complete.

Suggested status after fixed checks: IN_REVIEW. Clean STOP after scoped commit. Reviewer/Root acceptance pending.

## P2 input-projection ordering repair — 2026-10-27

Original author `a7a9d710816c316e5719f9fcf5ed8da0b9b80e57` remains in history and was returned for independent P2; its prior checks are not a claim that this counterexample passed. Root authorized the same author/worktree to repair only this issue, with a new commit after fixed-source checks.

The new test `test_oversized_trusted_input_is_terminal_before_credential_preflight` uses the existing trusted TimedTranscriptCueWrite/EvidenceTextBindingWrite constructors and a 165000-byte public synthetic caption; no SQL bypass, corruption, long-title shortcut or fake source authority. Normal reserve → sealed verified input → exact permit → immutable OWNER_QUALIFICATION consent is retained. The pure `_request` first proves the UTF-8 ceiling rejection. On a7 the service test then fails at `assert lookups == []`: actual `['credential']`, wire0, with misleading original credential/model waiting accounting. This is the reviewer's confirmed counterexample, independently reproduced as a real RED.

The eight-line product delta is only in the reserved new-pair continuation: after existing permit/consent validation and before `_model_ready`/credential preflight, call the existing pure `_cloud_request_preview`. Its typed unsupported-input refusal now finishes through the existing transaction/accounting as `REJECTED_EVIDENCE`, invocation_count0, outcome `CLOUD_INPUT_NOT_SUPPORTED_BEFORE_TRANSPORT`. No new status, receipt/table, schema, budget policy, qualification, adapter wire/profile or old-provider behavior. Valid inputs retain the same claim/dispatch path; no exception is allowed to strand this valid reserved oversized fixture as an orphan PENDING.

The regression asserts credential lookups0/wire0, unmodified consent and physical DATA, NULL actual identity/usage/cost/HTTP, no PENDING or new response-failure receipt, valid audit database and stable terminal result/all SQL+DATA after normal restart/no replay. The focused RED command is the explicit task environment/interpreter prefix followed by `-m pytest -p no:cacheprovider tests/integration/test_bigmodel_distillation_transport.py::test_oversized_trusted_input_is_terminal_before_credential_preflight -q --tb=short`. Initial RED1FAIL1.82s; repaired focused1PASS1.98s, then explicit wire0 assertion added. No existing assertion was removed/weakened. Final repaired-source complete12-file group: **579PASS**,384.83s, one expected duplicate-path ZIP fixture warning; actual subprocess exit0, not an interrupted run. Full command/output and before/after165 source/SQL/new-test hashes are preserved in `.var/bigmodel-transport/p2-repair-affected.json` and `p2-repair-affected.log`; `source_unchanged=true` and current files match the recorded final hashes. Log SHA256: `7a7bd3227ef398c96b16301fd5eb959b22a45b0feee8494c4ad21f7b39123024`. This run overlaps the original578/focused counts; totals are not added.

Strict mypy all122 source files PASS; in-memory compile122 PASS; Ruff no-cache changed source/tests PASS; diff whitespace review PASS. Sixteen adapter/wire/shared-prompt source segments, including the entire new BigModel adapter and native transport, are byte-identical to a7. All41 SQL resources are byte-identical to a7. Only the eight-line new-pair continuation check, one added trusted regression and this handoff change in the repair. Normal eligibility, budget policy, all existing wire/profile identities and every prior assertion remain unchanged. No real network/credential/model/owner operation. The original a7/P2 rejection remains historical; the new repair commit awaits Root's independent re-review and is reported in final chat. Clean STOP after committing.
