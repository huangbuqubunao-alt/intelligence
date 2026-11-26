# TASK-025A 交接报告

## 元数据

- Task: TASK-025A — Saved Intelligence Persistence & Command Amendment
- Role: Implementer; independent Reviewer: `/root/task025a_review`.
- Started: 2026-09-08; reported: 2026-09-09.
- Base/START_HEAD: `eb002b64649495d9b2567ade13b08117a877118f`.
- Worktree: `/Users/developer/Documents/yia-worktrees/task-025a-saved-intelligence`.
- Branch: `codex/task-025a-saved-intelligence`.
- Authority commit: `91be8f9`; implementation: `28c87b233d0d474162806ad1f5d9d4f9d74da1f1`;
  reviewed fix: `80f2da53a99d36c99b1990c5cb3b90a1d76da1be`.
- Final evidence commit is the commit containing this report (resolve with Git).

## 目标与范围

Product Owner explicitly assigned missing frozen V1 Save persistence to TASK-025A.
TASK-026's missing ownership blocker is resolved without reducing its Save scope.
Task graph, migration sequence, acceptance/impact matrices and downstream task/prompt
prerequisites were amended. TASK-025A alone owns m014, v013→v014. TASK-026 and
TASK-027 own no migration; neither task was implemented or started here.

Save stores only stable Intelligence identity and backend UTC saved_at in the
single local context. Duplicate Save retains saved_at; Unsave removes only this
relation; later Save starts a new saved_at. It does not copy a card or freeze a
revision. Existing FK RESTRICT history/dependency protection is preserved.

Typed `SaveIntelligence` / `UnsaveIntelligence` take identity only.
`SavedIntelligenceService` admits Save and resolves every Saved item using
TASK-019's existing `AuthoritativeIntelligenceReader` / `VerifiedIntelligenceRead`.
The read envelope is not a trusted type. Rejected current reads retain relation
metadata and a finite UNAVAILABLE code, never raw-content fallback.
All six claim kinds and DISPUTED remain unchanged. Current legal revisions are
followed, not snapshotted. Write-time revision preconditions close admission races.

Bounded local API seams (no frontend wiring):

- POST `/api/v1/saved-intelligence/save`, identity-only JSON.
- POST `/api/v1/saved-intelligence/unsave`, identity-only JSON.
- GET `/api/v1/saved-intelligence`, keyset page limit 1–100, paired cursor.
- Existing Intelligence detail endpoint supplies legal card/evidence detail.
- Stale Save admission: HTTP 409 `SAVED_TARGET_CHANGED`, safe message only.

No Preference/Feedback, Topic/pin, Weekly, Source policy, Intelligence truth or
revision mutation; no provider/model invocation or resource-ledger model entry.
No UI, folders/tags/collections, second trust root, V2 or Deep Analysis execution.

## 实际复用与来源

- DIRECT: Python standard-library sqlite3, dataclasses, datetime and existing
  pinned project dependencies. No new/upgraded dependency or lockfile change.
- ADAPT: existing repository transactions, SQL migration packaging, local API
  validation/loopback guard, safe error conventions and pagination patterns.
- DIRECT: existing TASK-019 trusted reader, unchanged. Existing deterministic
  TASK-025 fixture helpers admit test Intelligence via legal backend contracts.
- REJECT/DEFER: new bookmark libraries, account architecture, copied card stores,
  generic mutation APIs, UI and model transports: unnecessary/out of scope.
- No copied third-party implementation. Existing project licensing/release
  blocker remains unchanged; scanner wheel-license warning is not resolved here.

## 验收证据

| 验收项 | 结果 | 证据 |
|---|---|---|
| Approved lineage | VALID | cat-file exit 0; TASK-024 anchor ancestor exit 0; ancestry log includes 54dd03a and eb002b6 |
| Migration | PASS | Fresh14; seeded13→14 preserves exact rows across all prior domains; empty Saved; rollback/checksum tests; no015 |
| Packaged migration | PASS | Offline wheel/sdist contain014; isolated wheel import creates fresh14 empty Saved; packaged upgrade also checked before fix |
| Save/Unsave | PASS | Idempotency, backend time, 8 concurrent Saves, bounded keyset pages, identity validation |
| Single trust boundary | PASS | Raw Intelligence + raw relation cannot become trusted; forged command payloads/types rejected; existing VerifiedRead cannot be minted |
| Invalidation | PASS | INVALIDATED/OVERTURNED and unavailable Evidence preserve metadata, reject ordinary trusted reads and allow Unsave |
| Separation | PASS | Exact all-other-table snapshots unchanged by Save/Unsave, including Preferences/Feedback, pinned Topic, Weekly and ledger |
| Current schema regression gates | PASS | Current-version expectations updated to14, historical m013 upgrade test remains explicitly13 |
| TASK-026 prerequisite | RESTORED | Typed Save → list Saved → Unsave seams available without schema/UI trust invention |

## TDD 与修复证据

Tests were introduced incrementally before each behavior. Observed RED cases:
fresh schema expected14/actual13; missing service/Unsave imports; Saved API route
not found; four noncanonical saved timestamps did not raise. Implemented only
the corresponding migration/service/API/UTC constraint, then reran to GREEN.

Legacy current-version tests initially failed on expected13 and new index/version
history. Updated exact current schema gates, not domain assertions. m006–m013
SQL remains byte-identical. The corrupt-Evidence test first proved the existing
deletion guard rejects deletion; only its disposable corruption fixture disables
that trigger to demonstrate fail-closed Saved reads after out-of-band corruption.

Independent review found P2 admission/write race (P0=0/P1=0): a verified Save
could overtake invalidation plus completed Unsave. Added deterministic interleave
test: `pytest ... -k changed_between` failed `DID NOT RAISE IntegrityConflict`.
Immediate transaction now compares current revision with the admitted revision
before insertion. Regression passes; API translates conflict to safe409. Reader
and truth semantics are unchanged; no revision is persisted in Save state.

## 检查结果

| Command/check | Result |
|---|---|
| `uv run --offline pytest -q --tb=short tests/integration/test_task025a_saved_intelligence.py` | 48 passed in 7.23s after fix |
| Independent focused rerun | 48 passed in 6.83s |
| Requested focused/prior regression selection | 415 passed in 45.22s before concurrency fix; post-fix full suite covers all |
| `uv run --offline pytest -q --tb=line` | 2197 passed, 1 skipped, 1 warning in 122.19s after fix |
| `uv run --offline mypy src` | Success, 54 source files |
| `uv run --offline ruff check .` | All checks passed |
| `uv build --offline` | Wheel and sdist built; existing uv-build/current uv version warning |
| Isolated packaged wheel runtime | Fresh schema14, Saved empty, m014 present in wheel/sdist, no015 |
| `git diff --check` | Clean |
| Frozen migration / frontend diff against START_HEAD | Empty |
| `bash scripts/security_scan.sh` | EXIT 1, count=11 accepted historical synthetic-fixture findings, new=0; NOT PASS |

Regression selection covered TASK-025/024/023B/023A/023/022/021/020/019/018A/018,
state schema/lineage, dispatch crash recovery and AMBIGUOUS, Deep Analysis
persistence, local API, orchestration/Source automation, scoring, Note V1/V2,
Verified Note V2 and Weekly V2. Post-fix full suite also covers the wider frozen
core. No real provider or model was invoked; fixture transports are deterministic.

Scanner FAIL fingerprints match accepted baseline exactly:

- `test_deep_analysis_persistence.py`: lines195/403, fingerprint d72693d06a177c8d.
- `test_kimi_deep_analysis_adapter.py`: lines128/149/150/158/162/169/175/194/201,
  fingerprint 5596714c56730240.

Existing WARN items include entropy/print checks and unresolved project license.
The full-suite skip is the existing canonical o200k provisioning-dependent test;
the warning is the existing deliberate invalid-enum Pydantic bypass test. Neither
was removed, weakened or hidden. Browser checks are not applicable: UI work is
explicitly prohibited by TASK-025A.

## Diff 复核

Only authorized Save backend/API/m014, schema version expectations, task authority
and evidence changed. Existing runtime doctor now expects14; frozen domain,
dispatch/scoring/trust semantics remain unchanged. No m006–m013 edits, m015,
production dependency, credentials, real Vault, provider or scheduler change.
No dirty predecessor worktree was moved/reset; `.workbuddy/` was not read/staged.

## Reviewer 结论

- Reviewer: `/root/task025a_review`, independent read-only review.
- Reviewed range: `eb002b6..80f2da5`.
- First review: P0=0, P1=0, P2=1; race repaired in80f2da5.
- Re-review: APPROVE; P0=0, P1=0, P2=0.
- Independently reran48 focused tests, checked range diff, reproduced API race
  returning409 with relation absent; confirmed TASK-019/prior migrations unchanged.
- Full pytest/build/scanner evidence supplied by main implementer above.

## 实现者结论与主控交接

Implementation: APPROVE; no unresolved TASK-025A finding or contract decision.
TASK_026_SAVE_PREREQUISITE_RESTORED: YES.
This closes only TASK-025A product integration prerequisite, not full V1 acceptance.
Product Owner retains downstream authorization; TASK-026 may restart from the
approved final evidence anchor. No TASK-026/027 execution, push, merge, tag or release.
No integration performed; final clean worktree and exact evidence HEAD reported
in the closeout response. Stop here.
