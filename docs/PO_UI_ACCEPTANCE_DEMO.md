# PO UI Acceptance Demo

## Purpose

This is a local, synthetic Product Owner review environment for the current
product truth. It runs the production React UI against the loopback local API.

## Safety boundary

- Runtime root: `.var/po-demo/` only (gitignored).
- Database: `.var/po-demo/state.sqlite3`.
- Data and report artifacts: `.var/po-demo/data/` and `.var/po-demo/vault/`.
- The demo does not load settings, credentials, a real user database, a real
  Vault, providers, YouTube, or scheduler execution. It binds the API only to
  `127.0.0.1`; the UI uses no external assets or network requests.
- Reset has no path argument and deletes only the fixed demo root. It refuses
  a symlink or non-directory at that location.

## Commands

From the repository root:

```sh
./scripts/start_po_demo.sh
```

Open [http://127.0.0.1:5173/](http://127.0.0.1:5173/). The header shows **PO
Review Demo**, from the backend `/api/v1/system` runtime projection.

```sh
./scripts/stop_po_demo.sh
./scripts/reset_po_demo.sh
```

Stop leaves synthetic data in place; reset stops demo-owned processes and
rebuilds the designated runtime on the next start.

## Demo data

- 5 sources and 12 synthetic videos.
- 2 persisted generic weekly reports: `2026 W35` and `2026 W36`.
- 4 automation records: Manual, Daily 08:30, Weekly Sunday 20:00, and Disabled.
- Historical successful, failed, blocked, and `AMBIGUOUS` runs.

Recommended source drawer: **Practical AI Engineering**.

Golden Video: **How teams turn AI roadmaps into decision systems**. Its
synthetic canonical transcript is readable, and scoring is read through the
production `AuthoritativeScoringReader -> VerifiedScoringRead` projection.

Unverified scoring sample: **A rough scoring draft without a trusted result**.
It has a synthetic raw scoring-like artifact, but no verified score is exposed.

AMBIGUOUS sample: **Provider result uncertain after an interrupted request**.
Its History explains that the provider may have received the request and that
the system will not automatically retry to avoid duplicate calls or charges.

## Truthful unavailable states

- Golden Video Note V1: `UNAVAILABLE` (`NOTE_REF_NOT_PERSISTED`).
- Note V2: `UNAVAILABLE`.
- Deep Analysis: `BLOCKED` because no qualified live provider exists.
- Weekly version: `UNKNOWN`.
- Weekly V2: unavailable.
- Weekly video linkage: `UNAVAILABLE_IN_CURRENT_AUTHORITY`.

## Manual PO review sequence

1. Start with `./scripts/start_po_demo.sh`, then open the URL above.
2. Dashboard: check 5 sources, 12 videos, attention count, next run, recent
   activity, and the blocked Deep Analysis statement.
3. Sources: open **Practical AI Engineering**; inspect policy, Daily 08:30,
   recent videos, and activity. Also use Needs Attention and Disabled filters.
4. Videos: open **How teams turn AI roadmaps into decision systems**. Review
   Overview, Transcript, Scoring, Note, Deep Analysis, and History tabs.
5. Videos: open **A rough scoring draft without a trusted result**; confirm no
   verified score is presented.
6. Weekly: inspect `2026 W36`, its readable generic report, `UNKNOWN` version,
   and unavailable linkage statement.
7. Activity or the ambiguous video History: inspect `AMBIGUOUS` and its
   no-automatic-retry explanation.
8. Settings: confirm OpenAI is credential-blocked (`0/2`), Kimi and Local are
   unqualified, and no provider is production eligible.
9. Stop with `./scripts/stop_po_demo.sh`.
10. Reset with `./scripts/reset_po_demo.sh` when a fresh synthetic runtime is needed.
