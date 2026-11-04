# TASK-READINESS-CLOUD-SPENDING-POLICY — design before implementation

- Implementer: schema44_guard_resume; 2026-11-04 Asia/Shanghai.
- Base: `f1cc9365ac5eb5dfec8ebf95c326bc0c528c6a26`.
- Own worktree/branch: `/Users/hua/Documents/yia-worktrees/readiness-cloud-spending-policy`, `codex/readiness-cloud-spending-policy`.
- Root task: `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/tasks/TASK-READINESS-CLOUD-SPENDING-POLICY.md`.
- Reuse DIRECT existing schema44 proof/claim/receipt and typed SynthesisBudget, Backup control/admission guard, safe directory walking and standard-library flock/atomic fsync. No schema/dependency/credential/migration changes or new provider engine.

## Design and risk boundaries

1. One finite synthesis policy, initially absent/disabled. Explicit settings update accepts exact backend profile/price hash plus cumulative CNY budget, per-request reservation cap and maximum count. Decimal strings convert exactly to integer microCNY; no floats, caller prices or authority flags. Updates compare journal revision and preserve drafts on conflicts. Configuration never dispatches, qualifies a model or enables QA execution.
2. A bounded append-history JSON journal and initialization anchor live in an owned subdirectory of the existing Backup control root, outside DB/DATA/archive membership. Safe managed-directory walking, owner/mode/link checks, nofollow file opens, cross-process flock and atomic write/fsync protect it. Readonly preview does not create or append journal state. Missing/corrupt history with an anchor or any normal synthesis authorization fails closed; it is never auto-reset to zero.
3. Each reservation durably records execution/proof/profile/price/wire hashes and exact reserve BEFORE DB claim. Existing normal DB authorizations must match journal entries; DB rows and external holds are counted once. Entries absent after restoring an older DB remain held. Every execution ID is consumed once, including explicitly aborted reservations. No inference of no-call from absence in a restored DB.
4. Each actual attempt uses a unique cumulative journal-backed SynthesisBudget scope, with all earlier held reservations/counts in its immutable prior fields. This preserves existing schema44 peer-policy consistency while allowing explicit cap edits and retaining holds missing from the current DB. Journal admission enforces aggregate caps under one cross-process lock; p.confirm_and_claim remains the sole atomic execution claim.
5. Reserve/claim occurs under the existing shared Backup admission guard and the journal lock; the lock is released before any network transport. This prevents Restore swapping DB during claim. A synchronous failure inside this no-network boundary may append a never-dispatched ABORT only after checking exact current zero-call/no-authorization state; uncertain/crashed reservations remain HELD. No costs are silently released from model-result metadata.
6. No automatic monthly reset, recharge, paid fallback, budget deletion or history reset API. Prices are the existing dated frozen profile estimate, not a billing guarantee/account balance. Real qualification and separately authorized trials remain pending. Actual K3.1 and QA execution remain closed even after saving policy.

Risks: cross-file atomicity is not possible between SQLite and the external journal; therefore journal-first persistence conservatively retains holds across crashes. If anchor creation succeeds but initial journal persistence fails, later operations fail closed rather than inventing a clean history. Wholesale user/administrator deletion of all protected local state cannot be reconstructed from an old DB; no automatic recovery/reset is offered. Bounded journal exhaustion requires explicit maintenance instead of truncation. These conservative limits are preferable to unnoticed replay or overspending.

## Acceptance and implementation results

Reported 2026-11-05 Asia/Shanghai. Suggested status **IN_REVIEW**; Root's focused delta review is pending. No main adoption or real model acceptance claimed.

### Implemented scope

- `cloud_spending_policy.py` is one bounded374-line module: exact positive decimal CNY→integer microCNY parsing; explicit finite cumulative/per-request/count policy; CAS settings updates; dated frozen price/profile acceptance; bounded hash-linked history and initialization anchor; safe ownership/mode/link checks, shared Backup admission and cross-process flock; atomic write/fsync; exact DB/journal accounting and replay protection.
- Limits are finite: cumulative/per-request up to10,000 CNY, up to1000 held requests, up to5000 events/4MiB journal. These are reservation limits, not a bill/account balance or guaranteed billing maximum. No monthly reset, deletion/recharge/reconciliation endpoint, new schema, dependency or billing platform.
- Every attempt has a unique journal-backed scope carrying earlier held totals/counts as immutable prior fields. DB claims are verified and deduplicated with entries, including proof/wire/price/reservation/scope/prior/cap checks. Holds absent from a restored DB persist; existing claims without journal history refuse initialization. Synchronous proven preclaim failure appends ABORT and leaves a cancelled zero-call checkpoint. SystemExit/crash/unknown outcome remains HELD. Consumed IDs are never replayed.
- Narrow existing service hooks add readonly policy/estimate readiness and confirmation through the same proof-bound reserve/claim lifecycle. Actual transport/network remains outside the journal lock. Policy revision drift requires a new review. No provider/qualification authority is accepted from HTTP.
- GET/PUT `/api/v1/settings/cloud-spending-policy` accepts only finite settings and exact price acknowledgement, never prices, endpoints, OWNER_QUALIFICATION, eligibility flags or budget objects. Actual runtime supplies the store but keeps K3.1 unqualified, transport disabled and QA execution disabled. Legacy K2.6 behavior remains unchanged.
- Small91-line settings panel shows dated estimates, held/remaining reservations and cumulative count. Saving is explicit and authorizes no request. Conflicts preserve the entire draft, reload keeps the draft, and resaving requires new acknowledgement. Cloud preview shows the exact estimate, cap/history blockers and direct budget link preserving Content return. Settings and the legacy review explicitly guide users to select K3.1 for this policy; the legacy default is preserved and no paid model is silently selected. Only a proven zero-call abort permits a fresh explicit review command; unknown dispatch is never automatically retried.
- Missing/corrupt financial history is a cloud-only blocker. Actual factory still starts, reads Content/Evidence/trusted cards/saved state, and permits valid quiescent Backup. Restoring a valid claimed backup into a new owned root gives UNKNOWN financial totals and closed cloud execution; it cannot bootstrap zero costs.
- The historical frozen descriptor/date/hash and all migrations/dependency/lock/config files remain byte-identical to the base. Root's separate2026-11-04 official price check did not rewrite old proofs. The earlier1.943326 CNY QA reservation ledger remains independent, unmodified and not re-counted as normal-policy charges. Actual bills remain UNKNOWN.

### Actual checks

Interpreter: existing `/Users/hua/Documents/yia-worktrees/end-to-end-user-readiness/.venv/bin/python`; `PYTHONPATH=src`, strict additionally `MYPYPATH=src:tests`. Existing frontend node_modules reused via ignored symlink, with no package changes.

| Check | Actual evidence |
|---|---|
| Complete new `tests/unit/test_cloud_spending_policy.py` | **46 PASS, 36.18s**, `.var/cloud-spending-policy/new-tests-factory.log` |
| Complete affected synthesis runtime, QA-launch isolation, runtime composition, cloud wait cancellation, synthesis persistence, Backup/Restore and personalized distillation files | **436 PASS, 309.64s**, one existing duplicate-ZIP warning; `.var/cloud-spending-policy/affected-backend.log` |
| Complete frontend spending settings / existing model settings / cloud preview files | **58 PASS, 2.60s** (5+18+35); `.var/cloud-spending-policy/frontend-focused-profile-guidance.log` |
| Strict mypy complete source plus new financial test | **132 files PASS** |
| Ruff complete source plus new financial test | **PASS** |
| Compileall affected Python files | **PASS** |
| Final frontend typecheck and isolated production build | **PASS**; 54 modules, no served/deployment claim |
| Base/working diff whitespace check | **PASS** |
| `git diff --quiet f1cc936 -- system_synthesis_profile.py migrations pyproject.toml uv.lock frontend/package.json frontend/package-lock.json` | **PASS**, no changes |

New cases cover exact/invalid money and authority fields, configure-with-zero-calls, physically readonly review, one claim/one wire, restart totals, all three caps, two independent store/service instances confirming concurrently, duplicate confirmation, CAS/cap edits preserving unknown holds, explicit synchronous abort versus crash, and real older valid Backup→later request→Restore. Restore retains the external journal byte-for-byte, does not re-enable a disabled policy, refuses the earlier exact ID and counts its missing-DB hold once in the next distinct request's prior fields.

Three actual-factory cases cover missing/corrupt journal and valid backup restoration into a fresh owned project. They assert readable Content/Evidence/trusted card/saved state/Backup, UNKNOWN financial totals and zero closed-factory wire calls. Only external model transport/future eligibility and credential store are simulated; no real model qualification or bill is inferred. Frontend tests verify explicit settings acknowledgement, integer/decimal payload, no model/credential calls, preserved conflict drafts, unreadable history closed state, Chinese copy, estimate links and a fresh review only after a proven zero-call abort.

### Preserved failures and corrections

- Initial new-file run: **32 PASS /1 FAIL** (`new-tests-first.log`), because the total-budget fixture set per-request1 CNY above its smaller cumulative total. The API correctly rejected invalid settings. Fixed the fixture's per-call cap to the same exact estimated amount; no assertion removed.
- Next run: **37 PASS /1 FAIL** (`new-tests-second.log`), because the Restore test reused the restart-requested Backup instance and correctly received `CLOUD_EXECUTION_DISABLED` before replay checking. Rebuilt fresh service/policy/Backup instances as a real restart requires, without resetting flags/history; the final Restore and actual-factory tests pass.
- Intermediate complete files43/43 passed (`new-tests-third.log`, `new-tests-fourth.log`); the final46 include the additional real-factory isolation cases. No intermediate failure counted green or hidden by skips/deletions.
- Initial strict checking found a reused `result` variable conflicting with existing SourceCheckResult typing; renamed the policy-specific variable. Import sorting was confined to touched imports. Final strict/Ruff pass without ignores or assertion weakening.

### Remaining limits and safety

- Real K3.1 qualification and a separately authorized actual trial remain pending. Saving finite limits does not make ordinary paid use available by itself. No actual model/external network, Native Keychain, new fee, production configuration/data, main merge/push/deployment or formal owner data action occurred.
- The47-minute global backend and headed macOS acceptance were deliberately not run; Root will perform final global verification once after source/qualification freeze. Frontend checks here are automated UI tests/build, not a headed GUI claim.
- Protected external history must remain available independently of restored DB/DATA. Corruption/missing history gives a cloud-only fail-closed state; no automatic reset or inferred zero is offered. Whole-administrator filesystem deletion/rollback cannot be reconstructed from an older DB. The documented conservative crash holds and bounded journal maintenance limit remain.
- Implementer stops with a fixed commit and clean worktree; Root review/acceptance pending.
