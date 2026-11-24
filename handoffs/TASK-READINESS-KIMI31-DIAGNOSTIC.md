# TASK-READINESS-KIMI31-DIAGNOSTIC — implementation handoff

Base `b080d26aa260eb02ca740427630fdb0670959f67`; QA-only, pending Root bounded review. No actual prepare/execution, key/Native access, network, oracle reading, qualification or product persistence occurred. Only the new script, self-contained fake tests and this handoff change.

## Result and boundaries

`scripts/validation/kimi_public_diagnostic.py` has only fixed `prepare` and `execute` CLI modes. Target is **kimi-k3.1-pro**, fixed Moonshot HTTPS endpoint, thinking effort low, max_completion_tokens **6144**, JSON/nonstream, explicit implicit cache/5m, no tools/sampling overrides/retries/continuation. Three original public ZH v3 messages remain unchanged; old BigModel input/context identity is frozen **source provenance**, never new execution authority. No old adapter, consent, SQL, card, qualification or runtime is called.

Preparation verifies the three pinned public source files and three official local snapshots, freezes their bytes, all imported production Python source plus the new script, target profile, origin and final wire hash. It writes only `.var/kimi-public-diagnostic/package` in this worktree. No oracle or actual model output is opened. Root prepares the actual package after reviewing the fixed source; therefore no actual prepared SHA is claimed here.

The external ledger is fixed at `/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/kimi-public-20261029-ledger`, outside product Restore/package/worktree selection. A flock and O_EXCL record plus file/directory fsync precede credential resolution; identical case identity blocks copied-package replay. Reservation is never released. Restart after an interrupted reservation appends `RESERVED_UNKNOWN_STOP`, without key or send. Up to eight reservations/8,000,000 micro-CNY, each <=1,000,000; any prior failed/unknown/unreviewed case prevents the next case. There is no next-case CLI. A later separately assigned case would require Root's semantic PASS tied to the previous exact public-final hash.

Only execute can lazily resolve Native service `com.huangbuqubunao.intelligence.qa.kimi-public-20261029`, account `api-key`; no environment/old M12/production/BigModel fallback. Both pre-key and pre-wire validate current code/source/package/review. HTTP uses normal TLS, one POST, no redirect, a 300s absolute watchdog, no implicit reconnect, and <=2MiB response. Late DNS/TLS completion cannot POST. Unknown failures retain the reserve and bill UNKNOWN.

Only a complete stop/expected-model/valid-usage JSON final can be saved, byte-exact as public content. The complete envelope is scanned for literal and Unicode-escaped key material, including reasoning, before storing any final; final thought markers are denied. No envelope/reasoning/message/exception text/headers/key are stored or printed. Persisted fields are finite status, request reserve, safe model/usage/finish, body hash and safe public-final hash. PUBLIC_FINAL_REVIEW_ONLY is not semantic PASS or product success.

## Pricing and assumption (not a hard billing guarantee)

Official snapshots in `/tmp`:

- model `0ed8094de8dedd0ae4dd1912e92c6d385e1a79e83313c1f82686d7943a5d6df1`
- chat `7a1e692601a4a00628fbbd88c2561df485f2505a933c0841c9015ffaa6bc32c6`
- pricing `921983646fa6f233bbe0a6275bf48c2fa594d124e6377d596986a16aab96569b`

The chat snapshot explicitly says completion usage includes reasoning plus final; do not add reasoning tokens again. Input worst price is 13+13 cache-write=26 CNY/M, output 68 CNY/M, TTL5m. Source messages total 18,503 UTF-8 bytes; `(18503+2048)*26 + 6144*68 = 952118` micro-CNY. **2048 framing tokens is the task's conservative estimate, not a provider-proven hard bound**. Script labels this assumption; actual usage above the estimated bound stops and bill stays UNKNOWN. No extra token-estimate request was made; 6144 was not silently reduced. Account entitlement, balance and actual charge remain unverified; voucher applicability is not assumed and no recharge happens.

## Evidence

Explicit environment for all Python checks: `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=<this WT>/src`; strict mypy also uses `MYPYPATH=<this WT>/src`. Interpreter is Root's existing `.venv/bin/python`.

- Initial new-file RED: absent script, then meaningful missing-review RED (`FileNotFoundError` before key); normalized to redacted refusal.
- Crash-recovery regression RED: `test_concurrent_once_and_crash_reservation_no_replay` asserted a durable unknown result; result file was absent. Added append-only recovery record, no replay/retry.
- Complete new test file: **32 PASS / 1.26s**, after the recovery fix. Covers pure preparation, exact wire/raw, no SQL writes, concurrent/idempotent/copied-package once, interrupted reservation, eight-attempt/prior-semantic/budget gates, source/wire/profile/review expiry tamper, missing key, post-key tamper, wrong/missing model, length/malformed/duplicate JSON/429/timeout/usage bound, final/reasoning literal+escaped secrets, thought denial, fixed TLS/one POST/no redirect/body bound. Real socket creation and Native get are denied in the fixtures; source/docs are synthetic temporary fixtures, independent of Root's untracked stock.
- Compile/AST: both new Python files PASS without bytecode writes.
- Strict mypy: **2 files PASS** (correct local MYPYPATH).
- Ruff: both files PASS. Diff whitespace check PASS.
- All **213 tracked `src`, `migrations`, `scripts` files byte-identical to base**. No old tests, source, 001–043 SQL, actual packages, oracle, configuration or dependencies changed. No unrelated full backend/frontend/repeated review runs.

## Root-only commands after bounded source review

These commands do not contain credentials. Keep the `/tmp` official snapshots and original pinned public files available. Do not reuse any other credential namespace. Preparation alone does not authorize execution.

```sh
cd /Users/developer/Documents/yia-worktrees/readiness-kimi31-public-diagnostic
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" /Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python scripts/validation/kimi_public_diagnostic.py prepare
```

Root inspects the concrete frozen package/hash, then exclusively writes `package/review.json` with exactly these fields: decision APPROVE; prepared_sha256 from prepared.json; review_commit the actual 40-hex review commit; reviewer Root; max_calls 1; total_authorized_microunits 8000000; expires_at a future timezone-aware ISO timestamp. That receipt records Root's bounded review, not a cryptographic token or permission for other cases. Date guard is October 29 UTC; on a later date stop for current pricing/profile review, not a quiet override.

Only after source + concrete package acceptance and Root's isolated credential setup:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" /Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python scripts/validation/kimi_public_diagnostic.py execute
```

At most one send; **any result stops**. Preserve the external reservation/result and exact public final (if safe), then conduct independent semantic review using the unchanged original oracle. No retry, next case, normal eligibility or bill claim follows automatically.

## Reuse

DIRECT: Python stdlib flock/HTTP/TLS/fsync/hash/JSON and existing lazy Native Keychain wrapper. ADAPT: repository canonical/write_once/privacy protections from `qualify_bigmodel_public_first_case.py` and the approved public v3 safe capture (`run.py` pinned `ee1860b8cccfea8a9f17514bb2866d8fc46a0d831c2ea642e55306dbe8caaa16`); no old execute/import side effects or global monkeypatch. Repository MIT terms; no new dependency or third-party code bundle.

STOP after fixed commit; Root review/execution remain outstanding.

## Root bounded review repair (delta after 92f9829)

Root found two P2s; original commit/failure evidence remains. No additional scope or actual preparation/call.

1. Real prior CASE `public-aircAruvnKk-zh-kimi-k3.1-pro` was rejected by the original history regex. The deterministic new test failed in `reserve()` despite a correct original raw hash and Root semantic PASS. Now only nonempty alphanumeric/underscore/hyphen segments separated by **internal single dots** are allowed; no leading/trailing/consecutive dot, dot/dotdot, slash or backslash. Original same-case replay guard stays unchanged; the fake next-case test alone changes the fixed CASE to exercise future history handling.
2. A length response previously produced UNKNOWN_STOP and discarded actual model/finish/usage. Strengthened test reproduced that failure. After complete strict envelope parse and the full-envelope secret scan, a small whitelist observer retains bounded model identifier (<=128 safe characters), finite finish enum, and only nonnegative integer token counters <=2^31-1. On later validation failure it stores OUTPUT_REJECTED_STOP with a finite failure_reason and usage_validation=OBSERVED_NOT_ACCEPTED. These observations are not accepted accounting, billing authority or qualification. Exact 6144 completion/6000 reasoning counters, malformed final, foreign model and out-of-bound usage are now diagnosable without storing partial final, reasoning, messages or exceptions. Unparseable/unknown/secret-bearing responses remain UNKNOWN_STOP; secret checks run **before** any observations. Successful raw/decoder gates and wire/profile/6144/pricing/reservation policy are unchanged.

Final delta evidence: **45 PASS / 1.57s** in the complete new fake file; strict mypy 2 files and Ruff PASS. Both new Python files compile. Existing 32 tests retained and strengthened; additional true dotted-history, traversal rejection, bad-final and pre-observation secret guard cases. All existing production/migration/old-script bytes remain identical to base. No broader suites/reviewers/network/Native/key/model/actual package touched. Root only needs to inspect this two-finding delta; STOP after repair commit.


## Root integration / test clock completion

Root independently reproduced original92 defects, accepted dce33d8 delta and atomically integrated as5e33ff0. The writer hit capacity after fully writing only the fixed fake-clock fixture/next-day refusal test. Root preserved the stopped writer WT and copied that exact artifact (SHA e633a0723efdf9ef7e1ec3c320641a37557f6f36b73dd271815d49424729a32c), independently reviewed it and ran the complete new file:46PASS1.84s, strict2/RuffPASS. Real script/date/profile and frozen prepared package remain unchanged; no expiry extension or extra calls. This is accepted QA-only integration, not product model qualification.
