# TASK-026 — Product IA Integration

## Scope and authority

- Base: `102f2dd1b3019cacf5b61b2e54b10f672f184360` (approved TASK-025A).
- No migration; fresh database remains `user_version=14`; `m015` absent.
- Reuse: `ADAPT` the existing React workspace, loopback local API, TASK-019
  reader, TASK-025A Saved service, TASK-023 Topic projection, TASK-024 Source
  Run projection, TASK-025 Weekly-v1 and TASK-020/021 settings projections.
- No new dependency, provider/model call, credential access, Deep Analysis,
  Daily, Ask, active Investigation, migration, push, merge, tag or release.

## Implementation and evidence

- Replaced the old first-level navigation with exactly Dashboard, Intelligence,
  Topics, Sources, Investigations and Settings. Videos, Activity, Saved and
  Weekly are no longer peers; Saved and Weekly are Intelligence subviews.
- Added a bounded identity list that re-resolves every entry through
  `AuthoritativeIntelligenceReader`; rejected entries expose only an
  unavailable state. Saved preserves its relation but never supplies a second
  trust root or raw-content fallback.
- Dashboard is intelligence-first, with Topics, Weekly and finite attention
  before secondary source count. Sources display legal policy/filter/Source Run
  context and use the existing Check Now/manual-analyze routes. Investigations
  and Deep Analysis are truthful V1-unavailable states.
- TDD RED: frozen navigation test initially failed `expected 6, received 3`.
  GREEN: frontend focused suite `4 passed`; local API/PO demo `17 passed`.
- Full pytest: `2198 passed, 1 skipped, 1 existing warning`.
- `mypy src`, Ruff, frontend typecheck/build, offline build and diff check pass.
- Security scanner exits `1` with exactly 11 accepted historical synthetic
  fixture findings and no new finding; this is not reported as PASS.

## Browser/review

- Browser validation used a worktree-owned PO-demo API on loopback port 8766
  (the occupied unknown process on 8765 was not touched) and confirmed the
  exact six-element accessibility navigation, an intelligence-first Dashboard,
  evidence disclosure, Sources policy/detail context, Saved as an Intelligence
  subview, and Deep Analysis BLOCKED. The fixture creates its verified card
  through TASK-022's offline transport then re-reads it through TASK-019; the
  browser and API tests cover Save, Saved and Unsave without a provider call.
  It also finalizes a V1 Weekly snapshot from the legal Topic association for
  the preceding UTC week, then creates a later legal correction and lets the
  TASK-025 service add its visible `SUPERSEDED` marker. The fixture's execution
  guard still legally rejects Check Now. The unavailable-Saved product journey
  remains to be completed before TASK-026 may close.
- Adversarial fixes: fail-closed identity feed, unavailable Saved content,
  Save refresh reconciliation, no-success coloring for rumor/prediction/system
  inference, and incompatible projection resilience. P0=0; P1=0 in the
  reviewed slice.

## Remaining boundary

This records TASK-026 implementation evidence only. TASK-027 integrated
acceptance has not been started.
