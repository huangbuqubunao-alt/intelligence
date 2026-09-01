# Local product orchestration and frontend

## Run locally

Start the loopback API against a local state database:

```sh
youtube-intel serve-api --database /path/to/state.sqlite3 --port 8765
```

Then start the UI from `frontend/` with `npm run dev`. The Vite proxy forwards
`/api` only to `127.0.0.1:8765`. The API itself binds only to loopback and
does not emit CORS headers. Mutations require the `X-YIA-Request: local-ui`
header and a local Origin (when one is supplied).

## Product boundary

`POST /api/v1/sources` normalizes and persists an explicit Channel or Video
URL. It does not discover, download, process, score, call a Provider, write a
Vault note, or create Weekly output. Duplicate canonical URLs resolve to the
existing subscription.

`POST /api/v1/sources/{id}/check` is separate. Its application service is
fail-closed by default with `EXECUTION_GUARD_BLOCKED`; any future enabled
adapter must delegate to the existing runtime/discovery path and never to a
Provider SDK, raw SQLite mutation, or pipeline internals.

## Automation semantics

Migration 005 adds source subscriptions, source/video links, schedules, runs,
and a desired global Deep Analysis model preference. `scheduler-tick` is a
single bounded launchd-compatible tick: it uses SQLite `BEGIN IMMEDIATE` plus
the unique `(schedule_id, scheduled_for)` identity to claim due work once.
It has no daemon loop and no retry-until-success behavior.

For sleep/offline gaps, a tick claims at most one missed occurrence per
schedule and then resumes future cadence. It does not replay every missed
period. Disabled sources are excluded. Provider dispatch remains governed by
the existing v4 durable dispatch state machine; `AMBIGUOUS` remains terminal
and operator-visible.

## Provider and credential truth

The model preference is a *desired* setting, not an active production default.
Only backend qualification plus production eligibility can activate a model.
Current projections remain: OpenAI 0/2 credential blocked; Kimi 1/2
`SCHEMA_INVALID`; Local unqualified/search closed; active production default
`None`. The UI has no API-key input and the API accepts no credential value.

## Frontend delivery boundary

`frontend/dist` is intentionally ignored and is not included in the Python
wheel or sdist. The production UI always fetches local API projections; test
fixtures are confined to unit/E2E setup. Video scoring is not rendered unless
a future safe projection is explicitly wired through `AuthoritativeScoringReader`.
