# v0.1.0-rc.3 Private RC Candidate Evidence

Status: `READY_FOR_PO_RC3_AUTHORIZATION`

This document records the private RC-candidate audit based on authoritative
predecessor `7d8ecd465f70b4d2e1ac8dc71c535b3580d40a68`. It does not authorize or
perform a push, tag, release, publication, merge to `main`, or any change to
the immutable `v0.1.0-rc.2` tag.

The proposed future tag is `v0.1.0-rc.3`. It has **not** been created.

## Candidate disposition

- Engineering RC ready: **yes**.
- Real normal-production smoke confirmed: **no**.
- Live-smoke disposition: `BLOCKED_CREDENTIAL`; the required environment
  variable was absent, so the real provider call count remained zero.
- Remaining P0 findings: **0**.
- Remaining P1 findings: **0**.
- Product Owner decision required: whether to supply the credential for the
  single governed normal-production Source Run before authorizing the tag.

## Approved-history audit

The historical RC commit and every approved post-RC.2 landmark exist in the
shared object database. The RC.2 commit is an ancestor of the candidate base.
The ancestry path contains 22 single-parent commits and no merge commit.

| Authority | Approved anchor | Candidate result |
| --- | --- | --- |
| Historical private RC | `41233ee9aac647c99ef3c847130ef06624bbeaa5` | Immutable; peeled tag target unchanged |
| TASK-018B | `7cf0c9e2768701879f46086ecd51de94cd8767b6` | Present in ancestry |
| TASK-022B | `7a63c12cf9b7bbc85127f454455cfa1f610ae18d` | Present in ancestry |
| TASK-022C | `86e24588c753a529113e1886dd6c165dfb95feea` | Present in ancestry |
| TASK-022A | `a7531557542974aa05e7b9f5e4cbfe803a05e6a4` | Present in ancestry |
| NVIDIA adapter | `f1454ba1db61b01589811ec8986e1269473ab318` | Present in ancestry |
| NVIDIA qualification chain | `d9d72c06856270b5a55dab94ef8f426e89767fc9` | Present in ancestry |
| Qualification completion | `13c45bc4fcb379dbdbf81b667dee00a3ff140c29` | Present in ancestry |
| TASK-022D | `b32eac81fe0445f494581dd1713548d5882e6c27` | Present in ancestry |
| TASK-026A / candidate base | `7d8ecd465f70b4d2e1ac8dc71c535b3580d40a68` | Exact starting head |

## Integration matrix

| Area | Approved anchor | Current status | RC blocker? |
| --- | --- | --- | --- |
| Timed transcript | TASK-018B | Exact timed-cue authority retained; migration and trust tests pass | No |
| Evidence binding | TASK-018B | Exact binding, immutable hashes, and legacy `UNBOUND` behavior pass | No |
| Verified outbound input | TASK-022B | `VerifiedDistillationInput` and exact outbound-set checks pass | No |
| Cloud transport | TASK-022A | Governed NVIDIA transport; SDK retries disabled | No |
| AMBIGUOUS ledger | TASK-022C | Durable outcome, no redispatch, no fallback | No |
| NVIDIA adapter | NVIDIA adapter chain | Exact endpoint/model adapter present | No |
| Provider qualification | Qualification completion | Available and qualified for the exact V1 scope | No |
| Production authorization | TASK-022D | Exact provider/model/capability tuple only | No |
| At-most-once | TASK-022C/TASK-022D | Success, continuation, restart, scheduler, and AMBIGUOUS tests pass | No |
| Budget | TASK-023B/TASK-022D | Denial occurs before dispatch; cost `UNKNOWN` is not rendered as free | No |
| Resource Ledger | TASK-022C | Historical rows preserved; legal outcomes constrained | No |
| Dashboard | TASK-026A | Desktop/narrow browser acceptance passes | No |
| Intelligence | TASK-026A | Hierarchy and claim types remain human-readable | No |
| Evidence UI | TASK-026A | Trace visible; technical details secondary | No |
| Sources | TASK-026A | Friendly source names retained | No |
| Topics | TASK-026A | Disagreement state remains explicit | No |
| Weekly | TASK-026A | No-important-change state remains truthful | No |
| Saved | TASK-026A | Unavailable trusted content does not render stale detail | No |
| Settings | TASK-022D/TASK-026A | Exact scope shown; Deep Analysis remains unavailable | No |
| Frontend | TASK-026A | Tests, typecheck, build, and two-viewport E2E pass | No |
| Backend | Complete approved chain | Full and focused suites pass | No |
| Security | Release/security authority | 11 accepted synthetic fixtures, 0 new findings | No |
| Packaging | Release authority | Wheel/sdist inspected; required migrations present; forbidden artifacts absent | No |

## Verification evidence

- Backend: `2257 passed, 1 skipped, 1 warning` in the full suite; the warning is
  the previously accepted Pydantic serializer warning.
- Focused trust regression: `263 passed`.
- Migration probes: `8 passed`; fresh and representative upgrades reach DB
  user version 16, preserve foreign keys and immutable history, and keep legacy
  Evidence unbound where required.
- Frontend: `20 passed`; typecheck and production build pass.
- Browser: desktop `1440x900` and narrow `768x900` pass with zero console errors
  and zero unexpected external frontend requests.
- Static checks: mypy passes for 54 source files; Ruff and `git diff --check`
  pass.
- Security scanner: exit 1, exactly 11 accepted historical synthetic fixture
  findings, 0 new findings. This is not represented as a global scanner pass.
- Database/package: migrations 001 through 016 are included in both archives;
  m015 and m016 are present and m017 is absent.
- Frontend output and Python archives contain no provider key value/prefix,
  bearer literal, personal runtime path, qualification execution identity,
  qualification database, transcript fixture body, downloaded media, or
  worktree runtime artifact.

### Artifacts

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `youtube_intel-0.1.0-py3-none-any.whl` | 440247 bytes | `9d9285e7dffd3cbfcc47d57a345e969a37dbc9fa6ebcabf76f601f3ff1bbb934` |
| `youtube_intel-0.1.0.tar.gz` | 398994 bytes | `4dfe4044e14f158f42f9f5e52d6f6ce317f0b9bc6fe623e05a44838485b7f004` |

The artifacts were built offline and were not published.

## Provider and dispatch state

The sole production-eligible tuple is:

- Provider: NVIDIA NIM
- Model: `moonshotai/kimi-k3`
- Capability: `V1_VIDEO_DISTILLATION`
- Available: yes
- Qualified: yes
- Authorized: yes
- Production eligible: yes

No wildcard authority exists. Different NVIDIA models, different providers,
Deep Analysis, TASK-016G, Investigation expansion, and V2 remain unauthorized.
Production eligibility does not enable cloud use or spending by default.
Missing credential, unavailable provider, or denied budget produces zero network
calls. Provider fallback, model fallback, semantic retry, and SDK retry remain
disabled. Qualification execution identities cannot be reused by normal
production.

## Adversarial RC review

| Attack | Result |
| --- | --- |
| A. Unqualified provider/model dispatch | Blocked by exact sealed eligibility tuple |
| B. Kimi for Deep Analysis | Blocked; capability mismatch |
| C. Frontend forges authorization | Blocked; backend authority is decisive |
| D. Budget bypass | Blocked before reservation/dispatch |
| E. Missing credential dispatch | Blocked; zero calls |
| F. Production reuses qualification execution | Blocked by separate authority and identity |
| G. Successful execution redispatch | Blocked by durable at-most-once state |
| H. AMBIGUOUS redispatch | Blocked; zero retries |
| I. SDK silently retries | Blocked; max retries is zero |
| J. Provider fallback | Absent |
| K. Model fallback | Absent |
| L. Unexpected raw/full transcript outbound | Blocked by verified outbound input |
| M. Evidence outside exact outbound set | Blocked by binding/admission checks |
| N. Stale Saved content | Truthful unavailable state retained |
| O. Opinion rendered as Fact | Claim-type rendering distinguishes it |
| P. Unsupported claim admission | Blocked by trusted admission |
| Q. URL replaces human source name | Friendly source presentation retained |
| R. Provider details dominate primary card | Technical details remain secondary |
| S. Unknown cost shown as free | `UNKNOWN` remains unknown |
| T. RC.2 moves | Protected ref unchanged |
| U. m017 appears | Absent from source and packages |
| V. Secrets enter wheel/sdist | No matching secret material |
| W. Qualification DB/transcript/media enter package | None included |
| X. Release notes overstate capability | Scope and exclusions explicit |
| Y. Deep Analysis/TASK-016G/V2 leak | None authorized or marketed |
| Z. Main/remote/tag changes | None performed |

## Findings and bounded fix

During the first browser acceptance run, unrelated services already occupying
the default demo ports could satisfy the readiness probes and contaminate the
test. This was classified P1 and fixed with a regression-first change: the demo
launcher now rejects occupied loopback ports before starting either child.
The focused test went red before the change and green afterward; the complete
backend suite and browser acceptance were then rerun successfully.

- P0: 0 open.
- P1: 0 open; one P1 found and resolved in the candidate.
- P2: unresolved project license metadata remains a public-distribution
  warning. It does not block this private, non-published candidate.
- P3: the approved three-card Dashboard is intentionally vertically long at
  narrow height; no trust or usability blocker was observed.

## Private RC notes

Relative to immutable `v0.1.0-rc.2`, this candidate includes:

- real time-aligned transcript authority;
- exact Evidence binding;
- verified outbound distillation input;
- durable AMBIGUOUS Resource Ledger handling;
- production cloud transport;
- NVIDIA NIM / Kimi K3 adapter and real provider qualification;
- exact V1 production authorization; and
- real-data UX polish.

Deep Analysis remains unavailable. TASK-016G remains unauthorized. V2 is not
included. Public distribution is not authorized, and no unproven capability is
claimed.

## Stop condition

The engineering candidate is ready for Product Owner review. Because the live
credential was unavailable, the Product Owner must decide whether to supply it
for exactly one normal-production Source Run before any future explicit
authorization to integrate, privately push, or create the new immutable tag.
