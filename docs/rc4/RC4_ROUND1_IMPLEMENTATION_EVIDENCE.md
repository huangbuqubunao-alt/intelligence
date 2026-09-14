# RC4 Round 1 MUST Implementation Evidence

## Authority and scope

- Product specification freeze: `a633879f1fd19158edbfbc8487c2333c10b28cc0`.
- Implemented scope: UX-001, UX-002, UX-006, and UX-011 only.
- Runtime capability: V1 Video Distillation through NVIDIA NIM and
  `moonshotai/kimi-k3` only.
- Deep Analysis remains unavailable. TASK-016G remains unauthorized. V2 remains
  out of scope.
- Database `user_version` remains `16`; no `m017` or new durable state exists.

## Supported normal-production startup

The standard `serve-api` command now composes the existing durable Source Run
orchestrator with the authorized TASK-022D NVIDIA transport. Production use is
still fail-closed: the operator must explicitly enable Video Distillation and
set a bounded provider-call limit from zero through five.

`NVIDIA_API_KEY` must be injected into the Terminal environment by an approved
external mechanism before starting the service. The product does not accept,
persist, echo, log, or display the value. The startup shape is:

```sh
uv run youtube-intel serve-api \
  --database /absolute/path/to/state.sqlite3 \
  --enable-video-distillation \
  --video-distillation-call-limit 5
```

The key must not be added to a repository file or entered into the browser.
After changing the external environment, restart the service and use **Check
readiness** in Settings. Checking presence makes no model request.

The deterministic integration acceptance uses the normal API composition and a
mock only at the protected HTTPS transport boundary. It proves:

```text
frontend contract -> loopback API -> durable normal Source Run
-> TASK-022D normal-production authorization -> NVIDIA/Kimi transport boundary
-> admission -> AuthoritativeIntelligenceReader
```

It does not use qualification authority, a demo executor, direct provider code,
or manual database injection. Real provider calls in this round: zero.

## Readiness projection

`GET /api/v1/readiness` and
`GET /api/v1/sources/{source_id}/readiness` project independent server-owned
facts for:

- local application connection;
- supported Source processing composition;
- exact provider/model/capability eligibility and availability;
- server-side credential presence only;
- the bounded durable provider-call budget;
- Source existence, enabled state, and processing-policy readiness.

The frontend validates the complete response shape and fails closed if it is
missing or malformed. `Check Now` sends only its command identity; it cannot
submit readiness, credential, qualification, authorization, or production
eligibility facts. Backend preflight creates no Source Run and dispatches no
provider request when a prerequisite is blocked.

## Accessible Source configuration

Add and Edit Source surfaces expose named modal dialogs. Initial focus enters
the heading, Tab and Shift+Tab are contained, Escape closes only the topmost
dialog, and focus returns to the exact opener. While nested Edit configuration
is open, Source Detail is both inert and hidden from the accessibility tree.
Form failures use an associated alert summary. Existing visible focus styling
also covers the programmatically focused dialog heading.

Automated interaction tests and real Chrome acceptance cover open, traverse,
Escape, close, reopen, edit, and keyboard-submit behavior. This is a bounded
Source-flow acceptance, not a claim of full accessibility certification.

## Durable Source Run orientation

The API derives presentation from existing Source Run state, checkpoint
progress, child/execution links, and admitted Intelligence identities. No new
table, state machine, percentage, estimated time, or transient frontend truth
was introduced. Source Detail re-reads the projection after navigation/reload
and polls only while the latest durable run is active.

Terminal presentation distinguishes completed with admitted Intelligence,
completed with no important new result, failed/blocked states, and an
unconfirmed external result. Intelligence content itself remains available only
through the fail-closed `AuthoritativeIntelligenceReader` path.

## Finite safe recovery

| Condition | Safe action | Explicit non-action |
| --- | --- | --- |
| Credential unavailable | Open Run readiness; follow external Mac setup; restart and check readiness | No browser entry, storage, echo, speculative generation, or automatic retry |
| Budget blocked | Open Resource Usage and inspect the configured limit | No automatic limit increase, spending authorization, provider/model switch, or retry |
| Provider unavailable | Open readiness and check the same configured route later | No fallback, model/provider switch, Deep Analysis enablement, or protected redispatch |
| Source configuration | Open the affected Source configuration dialog | No guessed setting or automatic Source enablement |
| External result unconfirmed | View the affected run/Source details | No Retry, Try again, Continue, Resume, reset, or repeat |
| Explicit decision required | Open the exact Source context and save a user choice | No decision, continuation, Source enablement, or work start on the user's behalf |

The Dashboard change is limited to one compact summary for a current blocker.
Healthy readiness does not lift historical/non-blocking Attention above current
Intelligence.

## Verification evidence

- Focused readiness, API/startup, run projection, recovery, and PO demo tests:
  pass.
- Frontend interaction tests: `28 passed`.
- Frontend typecheck: pass.
- Frontend production build: pass.
- Mypy over `src`: pass (`57` source files).
- Ruff: pass.
- Real Chrome browser acceptance: pass at `1440x900`, `1280x800`, and
  `768x900` for ready, missing credential, budget blocked, provider unavailable,
  active run, terminal run, AMBIGUOUS, and Source configuration dialog states.
- Browser console errors: `0`.
- Unexpected external frontend requests: `0`.
- Real provider calls: `0`.

Final full-suite, offline build, scanner, diff, and Git evidence are recorded in
the implementation handoff after the final clean-worktree verification.

## Scope exclusions preserved

No UX-003 progressive onboarding, broad UX-004 Dashboard redesign, broad UX-005
validation redesign, UX-012 Resource Usage redesign/attribution, Save/Topic/
Weekly redesign, Investigations IA change, credential-entry/storage subsystem,
new provider/model, Deep Analysis, TASK-016G, V2, or migration was implemented.
The next authorized product action after Round 1 approval is the frozen
five-person moderated usability test, not additional implementation.
