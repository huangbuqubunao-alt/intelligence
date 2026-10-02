# V1X-DR-003: Phase 3 Home Knowledge Delta

Status: Owner-frozen Phase 3 implementation decision. Base:
`432f085d76824dfa51a447622aa2dba23ff8bfc8` (accepted Phase 1B).

Knowledge Delta answers “最近 7 天发生了什么变化？” / “What changed in the
last 7 days?” on one Home section. It is computed, never persisted, and is
independent of Deep Analysis qualification, Phase 1C and Phase 2. It requires no
model, generated explanation, external request, consent, or Obsidian integration.

## Time and authority inventory

One injected timezone-aware clock is called once per read. Convert that instant
to UTC before subtracting seven days: exactly 168 elapsed hours, including across
DST. The interval is closed at both ends: `[window_start, window_end]`. A record
one microsecond before start or after end is excluded. The existing ADR-003
fixed-width UTC RFC3339 microsecond timestamps preserve exact lexical ordering;
Aware legacy ISO forms are normalized by a deterministic SQLite function before
comparison, preserving microseconds and UTC offsets. Malformed/naive dates are
excluded rather than assigned an invented timezone. There is no SQL date
rounding or calendar-day truncation. Application timezone
(default Asia/Shanghai) travels in the read model for localized display. This is
not “since last looked”; no viewed/read/seen marker or watermark exists.

| Input | Meaning and actual timestamp |
| --- | --- |
| `videos` | Completed Content only: `pipeline_status = COMPLETE`, `completed_at`; discovery must not follow completion. `discovered_at` is discovery, not knowledge admission. |
| `intelligence_revisions` | Revision 1 `created_at` is admission; allocation of `intelligences` identity alone is excluded. Later revisions are coalesced per Intelligence. |
| `intelligence_state_history` | Explicit revision-specific prior/new state, `created_at`; NEW/UPDATED lifecycle noise is not rendered as a separate event. |
| `intelligence_revision_evidence`, `evidence` | Exact recorded Evidence membership before/after the window's revisions; set replacement is detectable even when counts are equal. No strength/support inference is made. |
| `topic_timeline_events`, memberships, membership Evidence and event dependencies | Existing meaningful, source-backed material events, `created_at`, grouped by active Topic. No name/rename/pin/update timestamp inference. |
| `source_run_state_events`, `source_run_checkpoint_events`, `source_runs`, `source_subscriptions` | Explicit repeated discovery blocking or subsequent completed source checking; event `occurred_at`. Current explicit SOURCE_CHECK_FAILED uses `last_checked_at`. |

The incorrect assumption `videos.created_at` is rejected: that field does not
exist. Generic `updated_at`, job retries, query completion and ordinary DB writes
are not knowledge changes. Newly discovered but unfinished Content is excluded;
its existing Content processing surface remains the place to inspect it.

## Product projection

`GET /api/v1/knowledge-delta` returns a typed, narrow envelope with window bounds,
timezone, availability and five categories: completed Content, new Intelligence,
revised Intelligence, Topics with new material, source health. Each has its exact
identity count and up to two representative items. Each item has change identity,
factual label, contextual original Content/Topic/source title (at most 240
characters), real navigation target, occurrence time and typed factual metadata.
No SQL row, error diagnostic, secret, generated narrative, raw state enum or card
conclusion is exposed by this new read model. Existing object readers retain
exclusive authority to present Intelligence/Topic conclusions when navigated to.

Newly admitted Intelligence that also changes in the window appears once under
new Intelligence, with its additional revision count. Existing Intelligence
appears once under revisions. The last revision in the window is selected by
revision number; category ordering is latest occurrence descending then entity
identity ascending. Evidence comparison is from the predecessor of the first
window revision to the last window revision; for new Intelligence it compares
revision 1 with its last window revision. It never calls additional Evidence
“stronger”. The last explicit non-lifecycle state transition is historical
metadata (“Recorded state”), not a claim that it is the currently trusted state.
Invalidation/overturning may be recorded without presenting the old conclusion
as current truth.

Topic counts are distinct active Topics with existing material events, not
Intelligence-plus-Topic events added to a global count. Topics are linked only
through existing owned memberships, exact revision Evidence and timeline
relationships. Phase 1A `knowledge_graph.topics` compatibility values are inert:
this subsystem never reads model/analysis JSON, never assigns Topics and never
reintroduces removed Deep Analysis model roles.

## Source health policy

Only enabled followed channels contribute. Exclude manual single-video analysis,
model/budget/selection/child failures, guard blocks and operational retries.
A discovery-blocked Source Run requires a BLOCKED DISCOVERY checkpoint and the
explicit EXECUTION_CONDITION_UNRESOLVED state event, with no completed discovery
checkpoint. At least two consecutive such attempts since the preceding complete
check, within the window, produce one factual “discovery repeatedly blocked”
item. A later completed check after that sequence produces “Source checks
resumed”. It does not assert new content resumed. Normal successful checking
alone is not a Delta. Explicit current SOURCE_CHECK_FAILED can show one failure
without pretending it repeated. Ordinary subsequent successful checks do not erase a recovery within the window.
Coalesce the latest meaningful applicable fact per source;
use event identity to break same-instant failure/recovery ties and never disclose
raw exception text. Recovery cannot be invented from the mutable
last-success timestamp alone.

## Bounded Home and failure

Use one SQLite URI `mode=ro`, query-only read transaction across all sources.
An absent database remains absent; reading must not create an empty file.
Five bounded SELECTs (four source projections plus revision-structure validation).
No per-item repository round trips and no unbounded frontend list. Category counts remain
exact while at most ten items are serialized/rendered. SQL sorting and identities
provide deterministic ties. Compact counts and grouped rows reuse the existing
Panel and CSS tokens; no primary navigation destination is added. Open targets
use the existing Content, Intelligence, Topics and Following surfaces. The old
unwatermarked pinned-Topic panel is labeled “Pinned Topics”, avoiding its previous
unsupported “since you last checked” wording.

A zero-change successful window says “最近 7 天没有明显的知识变化。” / “No
meaningful knowledge changes in the last 7 days.” A failed category has null
count, no details and explicit unavailable status; overall partial results are
clearly labeled and never called empty. All-source failure is unavailable,
never zero. The UI has loading and retry states; raw backend diagnostics remain
hidden. Original source titles are not translated; all product labels, state
labels, controls and dates follow zh-CN/en interface language.

## Persistence, restore and reuse

No migration, index allocation, durable Delta table, user watermark, cursor,
read/unread flag or Backup/Restore schema change. Restore the same authoritative
records and use the same clock to naturally recompute the same projection;
Delta output is never part of an archive. Migration ordinal 031 remains free
for other work. The read is side-effect free and emits no cloud/local model or
network call.

Reuse decision: DIRECT existing Python sqlite3/datetime/zoneinfo/dataclasses,
repository connection settings, loopback API and React/CSS/localization stack;
REFERENCE existing Home Panel and typed product projection patterns. No third
party code is copied; no dependency, lockfile or toolchain change is required.
Independent Phase 3 worktree only; no merge of Phase 1C, Phase 2, M13 or main.
