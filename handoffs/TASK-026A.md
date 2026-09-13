# TASK-026A Handoff — Real-Data UX Polish for V1 Production

## Metadata

- Task: `TASK-026A — Real-Data UX Polish for V1 Production`
- Authoritative predecessor / start head: `b32eac81fe0445f494581dd1713548d5882e6c27`
- Branch: `codex/task-026a-real-data-ux-polish`
- DB user version: `16`
- `m017`: absent
- Provider authority represented: NVIDIA NIM / `moonshotai/kimi-k3`, V1 Video Distillation only
- Real provider calls: `0`
- Push / tag / release / main integration: none

## Baseline UX audit

The application was captured before implementation at 1440×900 and 768×900 using its isolated PO-demo runtime. The capture observed zero console errors and zero non-loopback requests.

| Screen | Finding | User impact | Severity | Bounded fix |
| --- | --- | --- | --- | --- |
| Dashboard | Needs Attention preceded the user’s useful Intelligence. | A first-time user met system state before understanding product value. | P1 | Put current Intelligence, Topic changes, and the week first; show actionable attention last. |
| Dashboard | Empty-state language did not explain the next useful step. | A new user could not tell how to get value. | P1 | Say plainly that no important Intelligence exists yet and lead to Add Source. |
| All primary screens | A global Deep Analysis blocked badge competed with the page purpose. | Unavailable future capability appeared to define the whole product. | P1 | Keep Deep Analysis truth in Settings and Investigations, not the global header. |
| Intelligence | Claim kind and lifecycle led the card; conclusion, relevance, and novelty were visually flat. | Real results took too long to scan and Opinion risked reading like Fact. | P1 | Reorder to Conclusion → Why this matters → What is new → Important details → semantic labels → Evidence. |
| Intelligence / Evidence | Evidence was a collapsed string of internal identifiers. | A user could not readily understand which source, video, range, and excerpt supported a claim. | P1 | Show verified Source, Video, timestamp range, exact verified excerpt, and timestamped video link; keep IDs collapsed. |
| Intelligence | An unavailable historical projection appeared ahead of current trusted cards. | The first current-result impression was an error-like placeholder. | P1 | Current and Dashboard lists select only trusted AVAILABLE projections; Saved remains fail-closed. |
| Sources | A canonical channel URL could become the primary name. | A real source was difficult to recognize. | P1 | Prefer persisted display name, then persisted video channel name, then safe public ID; retain URL as Open Source. |
| Settings | Provider cards reflected obsolete unqualified state and foregrounded implementation detail. | Users could not tell what Kimi may legally do. | P1 | Present capabilities first: Video Distillation available only for V1; Deep Analysis unavailable; provider/model collapsed. |
| Responsive shell | At 768px, grid row sizing left a near-screen-height blank area before page content. | Primary content appeared missing below the navigation. | P1 | Switch the narrow shell to block flow and keep cards/actions within viewport width. |
| Weekly | Version/date/evidence metadata competed with the weekly meaning. | The page read like processed-record output rather than “what mattered.” | P2 | Lead with summary and Topic; collapse technical evidence references. |
| Topics | Lifecycle/independence detail was terse and technical. | Single-source uncertainty and unavailable support were easy to misread. | P2 | Lead with current understanding, explain independence in plain language, retain disagreement and timeline. |
| Sources | Initial History, Per-run Limit, Check Now, and Analyze this Video depended on prior product knowledge. | Configuration and overrides were ambiguous. | P2 | Add concise inline explanations without changing commands or policy semantics. |

Baseline totals: P0 `0`; P1 `9`; P2 `3`; P3 `0`.

## Bounded implementation

- Dashboard now answers “what matters” first and uses a useful empty/new-user path.
- Needs Attention projects user impact and legal next action without exposing runtime enums or inventing Retry.
- Intelligence cards preserve claim/state truth while giving conclusion, relevance, novelty, important details, and Evidence a human reading order.
- Evidence remains visible and traceable as Source → Video → verified timestamp range → verified excerpt. Exact internal IDs remain available only in Technical provenance.
- Source projections derive a friendly label only from persisted domain data; no lookup, migration, or fabricated name was added.
- Weekly, Topic, Saved, Source configuration, and narrow-viewport hierarchy were polished without changing their underlying semantics.
- Settings presents NVIDIA NIM / Kimi K3 truthfully as approved only for V1 Video Distillation. Deep Analysis remains unavailable and cannot be enabled here.
- The local PO demo represents all three governed qualification cases with public metadata and original paraphrases. It contains no qualification DB and no copied transcript body.

Backend change is limited to safe presentation projection: verified evidence excerpt, persisted Source/video display fields, and already-approved provider capability status. Trust, provider dispatch, policy, Weekly, Topic, Saved, and database contracts are unchanged.

## Real-data cases represented offline

| Governed case | Public identity | UI purpose |
| --- | --- | --- |
| Phase 1 | `aircAruvnKk` / 3Blue1Brown | Supported statement, updated lifecycle, friendly-name fallback, readable Evidence. |
| Phase 2 opinion | `7gtc1DW2Tgo` / Marques Brownlee | Attributed Opinion remains visually and textually distinct from Fact. |
| Phase 2 factual/technical | `wjZofJX0v4M` / 3Blue1Brown | Supported technical statement with video/range/excerpt traceability. |

## Browser review

Repository Playwright-core browser review ran against the loopback-only isolated demo at:

- 1440×900: Dashboard, Intelligence/Evidence, Saved, Weekly, Topics, Sources, Source onboarding, Source detail, Settings, Investigations.
- 768×900: the same ten surfaces.

Screenshots are review artifacts under ignored `.var/task-026a-audit/final/`; they are not committed. Automated assertions cover frozen top-level IA, no horizontal overflow, early narrow-layout content placement, friendly Source naming, visible Evidence, Saved fail-closed behavior, Topic disagreement, Check Now/no-Retry behavior, collapsed provider details, Kimi scope, and Deep Analysis unavailability.

- Browser desktop: PASS
- Browser narrow: PASS
- Console errors: `0`
- Unexpected external requests: `0`
- Primary internal-language leaks: `0`

## Ordinary-user review

| Question | Answer | Evidence |
| --- | --- | --- |
| Can Dashboard be understood in 5–10 seconds? | YES | “What matters now” and the strongest conclusion occupy the first content surface. |
| Can the most important Intelligence be identified? | YES | Conclusion is the card headline; system attention is subordinate. |
| Is relevance clear? | YES | Every available card has an explicit Why this matters section. |
| Can Fact/Opinion/Prediction be distinguished? | YES | Human labels preserve underlying claim kinds; the opinion fixture also states it is the presenter’s judgment. |
| Can a claim’s origin be verified? | YES | Source, video title, range, verified excerpt, and timestamped link are visible. |
| Is Needs Attention actionable? | YES | It states what happened, what remains unchanged, and the appropriate next step. |
| Is Kimi’s allowed scope understandable? | YES | Settings says V1 video analysis only; exact provider/model is secondary. |
| Is Deep Analysis unavailability clear without task language? | YES | Settings and Investigations state it plainly and do not expose task IDs. |
| Are Initial History and Per-run Limit distinguishable? | YES | Both setup and detail surfaces explain their different horizons. |
| Is Check Now understandable? | YES | It runs the Source under current policy and is explicitly not a retry action. |
| Would a normal user know what to click next? | YES | Empty Dashboard leads to Add Source; populated screens expose direct, labelled actions. |

## Adversarial product review

| Attack | Result |
| --- | --- |
| A. Raw fallback after trusted content becomes unavailable | Rejected: authoritative read remains first; Current filters unavailable projections and Saved shows only a fail-closed notice. |
| B. Claim label changes enum meaning | Rejected: display labels map one-to-one; backend values are unchanged. |
| C. Opinion looks like Fact | Rejected: Attributed opinion label and judgment wording remain visible. |
| D. Disputed information looks confirmed | Rejected: Sources disagree remains visible; no confirmed styling is introduced. |
| E. Source URL mistaken for Source name | Rejected: persisted friendly label is primary; URL is only Open Source. |
| F. Evidence becomes inaccessible | Rejected: Evidence is expanded primary card content; only IDs are collapsed. |
| G. Technical detail dominates | Rejected: provenance and provider/model details are disclosures below product meaning. |
| H. Empty Dashboard implies important Intelligence | Rejected: it states “No important new intelligence yet.” |
| I. Needs Attention implies illegal Retry | Rejected: no Retry is rendered; uncertain results explain that no automatic repeat occurs. |
| J. Kimi appears authorized for Deep Analysis | Rejected: Deep Analysis explicitly says unavailable and not authorized. |
| K. Settings implies cloud automatically on | Rejected: no enable action or automatic-on claim exists. |
| L. UNKNOWN cost looks zero | Rejected: missing token/cost values render as Unavailable. |
| M. Saved renders stale content | Rejected: unavailable target has no stale card and remains removable. |
| N. Narrow viewport hides Evidence/actions | Rejected at 768×900: no horizontal overflow; cards, excerpts, disclosures, and actions remain reachable. |
| O. Primary UI leaks task/enums | Rejected by all-screen visible-text audit. |
| P. Frontend reads DB/trust rows directly | Rejected: frontend uses only `/api/v1` application projections. |
| Q. `m017` appears | Rejected: migration set ends at `016`; DB is 16. |
| R. Provider/network call occurs | Rejected: demo uses injected offline transport; browser traffic is loopback-only. |
| S. Main/tag/remote changes | Rejected: task remains isolated; no push/tag/release/integration command ran. |

Final adversarial totals: P0 `0`; P1 `0`; P2 `0`; P3 `1` (a three-card Dashboard is intentionally vertically long, but its first card and all primary actions remain clear and reachable).

## Verification

| Gate | Result |
| --- | --- |
| Focused frontend | `20 passed` |
| Frontend full tests | `20 passed` |
| Frontend typecheck | PASS |
| Frontend build | PASS |
| Backend/product focused regressions | `259 passed` |
| Full pytest (single final run) | `2256 passed, 1 skipped, 1 existing warning` |
| mypy `src` | PASS; 54 source files |
| Ruff | PASS |
| `uv build --offline` | PASS; wheel and sdist built; existing uv version-range warning only |
| `git diff --check` | PASS |
| Canonical security scanner | EXIT `1`; exactly `11` accepted historical synthetic-fixture findings; `0` new; not scanner PASS |
| DB user version / migrations | `16`; `m017` absent |
| Package and lock files | unchanged |
| Frontend direct DB access | `0` |
| Real provider calls | `0` |

## Next authorized action

STOP. TASK-026A makes no integration or release authorization. The Product Owner may next authorize integration of the post-rc.2 V1 production chain into main and preparation of a new immutable private RC candidate. Do not move `v0.1.0-rc.2`.
