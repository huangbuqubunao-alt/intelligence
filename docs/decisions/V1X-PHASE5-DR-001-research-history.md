# V1X-PHASE5-DR-001: Research immutable revisions and History

Status: Implemented under the owner's Phase 5 goal, 2026-10-03.
Baseline: `22ea84a79bba3f27566a221e774c93c3cc797a4f`, schema 31.

## Definition and persistence audit

History answers which previous authoritative versions exist for one semantic
Research item. It does not answer what changed. Phase 4 `research_items` stores
canonical question, sorted selected-Content scope, output language, frozen
`research-lite-v1` contract, creation timestamp and current result identity.
`research_results` stores random execution identity, monotonic per-item execution
number, immutable canonical packet JSON, SHA256 payload seal, result identity and
aware UTC assembly timestamp. Each packet contains its exact question/scope,
language, contract/status, original Evidence identities/text/ranges/artifact/hash/
language/timestamps, and admitted Intelligence revision/conclusion/class/state/
source/Evidence membership/stances. Contextual Content titles are frozen labels.

**Phase 4 execution == Phase 5 revision.** User-facing revision id is the existing
sealed result identity; execution id retains its accepted backend meaning. No
redundant table, competing version identity or persisted display ordinal exists.
Stable semantic identity remains SHA256 of canonical contract/question/scope/
output-language input. Distinct languages/scopes/questions remain distinct items. Rerun preserves the
accepted server-configured output-language capture; changing that setting creates
a distinct semantic item rather than merging cross-language History.

Reuse classification: DIRECT existing SQLite transactions, schema 031, strict
ResearchPacket, Evidence resolver, recorded Intelligence reader, backup staging,
React/API/language/Panel patterns. ADAPT Research trusted reads and internal
routing. REJECT redundant revision storage, live reconstruction, model summaries,
Diff and new event systems. No dependency/toolchain changes or external source
exploration. Only Phase 5's independent worktree is writable.

## Current pointer and failures

Assembly verifies and appends the packet plus advances the composite-FK current
pointer in one `BEGIN IMMEDIATE` transaction. Failed persistence, verification or
pointer update rolls everything back. No failed-attempt row is a revision.
Completed insufficient-material packets are valid revisions. Old results cannot
be updated or deleted; semantic item deletion is also forbidden by existing
triggers. No new deletion API or forever-archive policy is introduced.

Current reads retain Phase 4's explicit pointer/latest-sequence check with no
fallback. History independently verifies older rows: corruption in current or
another old result cannot conceal unrelated valid previous authority. Failed
historical validation exposes no untrusted contents. List responses disclose a
page-local unavailable count, not a misleading complete trusted total.

## Trusted History API and ordering

GET `/api/v1/research/{research_id}/history` returns lightweight verified previous
revision metadata: revision id, assembly timestamp, canonical question, language,
Content/Evidence/Intelligence counts and material status. It excludes verified
current. GET `.../history/{revision_id}` returns the exact immutable packet using
the same complete Phase 4 row/provenance verification. Its separate `is_current`
read-context flag distinguishes an explicit current revision route without
changing the packet or Phase 4 current-result response. Both ids must match the
same persisted Research row; SQL values are parameters. Stable not-found,
corrupt-authority and invalid-cursor codes are localized by the client.

Rows sort descending by the existing unique per-item execution sequence. This
is authoritative production order, including timestamp ties or clock adjustments;
wall-clock timestamps remain display metadata. The existing unique index supplies
the order without adding schema. A stateless cursor binds Research identity,
initial maximum sequence and exclusive before-sequence. New reruns cannot shift
later pages. At most 25 candidate rows are verified/rendered per page, plus one
lookahead row for `has_more`. Cursor advances over unavailable rows too. Response
includes `next_cursor`, `has_more`, page bound and current availability. No packet
contents are sent in lists. Shared page Evidence is batch resolved; failed batch
resolution falls back to isolated validation so one broken reference does not
poison unrelated rows. Intelligence uses the accepted bounded recorded-card
reader (at most six interpretations per packet).

## Historical authority and product

Historical packets never replay retrieval or substitute newer Evidence or current
Intelligence. Stored references must continue to resolve under accepted authority
policy; unavailable/corrupt source authority makes that version unavailable.
Later legitimate Intelligence revisions preserve the recorded revision. Source
navigation starts with that packet's own Content/Evidence/Intelligence identities;
existing Intelligence navigation explicitly opens today's domain state.

History is a section in existing Research detail, retaining six primary
navigation destinations. Timestamp-first entries avoid ambiguous renumbering.
Historical deep routes reopen explicitly after reload/restart and show a read-only
previous-version label plus a return-to-current action. Assemble again creates a
new revision of the semantic item, including when initiated from an old packet.
Empty/loading/unavailable/pagination controls support zh-CN and en. No raw enums
or backend diagnostic prose become product copy. DESIGN.md remains the visual
reference; no redesign is introduced.

## Restore and boundaries

No migration is needed: schema stays **31**, preserving exact-schema archive
compatibility. Phase 4 backup verification already includes both tables, all
executions, sequence integrity, current pointers, triggers and source authority.
Multiple-version restore tests prove exact packets/order/current/source tracing.
Corrupt historical archive authority is rejected before replacing live state.

History is read-only and does not mutate Research, Intelligence, Topic or Home
Knowledge Delta. No watermark/unread/view-state, cross-feature event, cloud/model
call, web call, comparison, textual/semantic Diff, generated revision summary or
persisted Diff/cache exists. Phase 6 can explicitly request two stable revision
ids and derive a comparison later; Phase 5 computes none.
