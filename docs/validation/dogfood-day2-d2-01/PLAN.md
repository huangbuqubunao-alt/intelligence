# D2-01 local video import

Base: main/origin/main ce60189f002270909e5ef234deedb61ceba19b0f, clean after fetch.
User's complete independent goal is the task/authorization package; it supersedes
historical workflow restrictions on self-review, main adoption and private owner
relaunch. No Phase 14 or other Day 2 fixes. Schema stays 35.

Done: prove original focus/refresh regression before repair; preserve selection
and in-flight upload across rerenders/page navigation; navigate committed success
to Content with honest processing state; no duplicate submissions; isolated real
UI/API/database validation; required checks, diff self-review and final regression;
ff-only main adoption, push and provenance-verified owner frontend update.

Scope expected: workspace App/AddEntry/LocalImport and bilingual copy, focused
frontend/backend regression tests and this evidence/handoff. DIRECT reuse of
existing React 18.3.1 (MIT), locked Testing Library/Vitest/Playwright tooling,
LocalContentProvider, normal runtime composition, SQLite and owner launcher.
No new dependencies, schema, auth, cloud, production config or user-record edits.
DESIGN.md is the persistent existing design reference; existing modal/status
styles, native labelled controls, live messages and 320px wrapping remain.

All test media are synthetic. Database/config/vault live only in candidate .var
or pytest temporary directories. Owner database inspection is read-only. Owner
protected table digests and filesystem digests are compared before/after; no UI
import is performed on owner. Protected historical worktrees are read-only.

Live owner facts: whole-database digests naturally change while owner is in use.
Before adoption, owner still has zero Video/Content snapshots; differences are
limited to source/tracking/check/run/event state. Read-only inspection confirms
new MANUAL_CHECK_NOW runs while this task was testing only isolated ports.
Historical-worktree and owner-file fingerprints remain identical. Report ongoing
owner use and zero fixture pollution, rather than claiming a frozen database.
