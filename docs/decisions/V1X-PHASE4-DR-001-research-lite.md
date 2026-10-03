# V1X-PHASE4-DR-001: Research Lite

Status: Owner-frozen Phase 4 implementation decision, 2026-10-03.
Authoritative base: `ba9f27fd2869e24a0b30e58f3ef6e5e29c747a7b`, schema 30.
This is new V1.x scope and does not rewrite historical V1 decisions.

## Product and inventory

Research Lite answers what relevant authoritative material the user already has
within an explicit selected library scope, and what they can inspect reliably.
It deliberately assembles evidence and existing interpretations; it does not
invent a new answer, consensus, or verified conclusion. No chat, autonomous web
exploration, ingestion, Summary regeneration, Deep Analysis dispatch, Intelligence
promotion, Topic mutation, Knowledge Delta mutation or Obsidian write occurs.

Inspection found no production Research contract, runtime, provider, API, table,
or Obsidian projection. The word “research” in the Summary system prompt describes
an analyst role and grants no Research capability. The PO demo has a Content title
containing “Research”; that title is not a Research artifact.

| Existing piece | Classification and decision |
| --- | --- |
| `frontend/src/demo-v1/WorkspacePages.tsx` Research page | DEMO-ONLY / KEEP HISTORICAL. Mock scope and version controls are not activated. |
| demo `model.ts`, `fixtures.ts`, App routing, Search, Onboarding, translations/styles | DEMO-ONLY / KEEP HISTORICAL. Research History, versions and Diff fixtures are not authority. |
| `frontend/demo-v1` design and historical frontend E2E | REFERENCE / KEEP HISTORICAL. No fixture is imported into the live Research path. |
| live workspace App, language context, API client, CSS/Panel patterns | REUSE / ADAPT. Maintain accepted IA and source navigation. |
| shared Evidence/text bindings/timed cues and backend resolver | REUSE. Exclusive Evidence authority; never mint new Evidence. |
| Intelligence current-card reader, revision graph, classification and stances | ADAPT. Current admission for assembly; explicit recorded-card validation for immutable provenance. |
| Intelligence append-safe revisions | PATTERN ONLY. Research uses separate domain tables. |
| Deep Analysis Phase 1A provider/candidate records | DORMANT/UNSAFE as Research inputs; never read. |
| Deep Analysis Phase 1B claims and model routes | DEFER as synthesis input. Existing promoted durable Evidence is independently resolvable through shared Evidence authority. |
| Topic memberships, Following/source links | REUSE only for existing Intelligence provenance. Broader Research scope is deferred. |
| Home Knowledge Delta | KEEP SEPARATE. Its presentation is never source authority. |
| accepted live Search | No standalone authoritative production search found. Use bounded parameterized Content filtering and deterministic scoped lexical retrieval. |
| Backup/Restore and migration lineage | ADAPT. Include Research and reverify every archived execution. |

The live accepted navigation has six primary destinations: Home, Following,
Content, Intelligence, Topics, Settings. Unlike the demo, it has no Research
placeholder. Preserve these six. Intelligence opens a dedicated Research view;
`#Research` and `#Research/<semantic-id>` are restartable internal routes. No
seventh primary destination, duplicate Research surface or History UX is added.

## Contract, scope and retrieval

An explicit user question is required: 1–2,000 Unicode characters, surrounding
whitespace trimmed, internal whitespace/case retained, disallowed control bytes
rejected, including invalid Unicode surrogate code points. It is never rewritten into a different question. Scope is 1–20 explicit
existing public Content ids, sorted and deduplicated. Raw scope ids are validated
and always SQL parameters. Empty/missing/oversized scopes fail honestly. Topic,
Following and “all library” scopes are not supported; compatibility topics and
similar source names cannot grant scope authority.

Content selection is paged (50), filterable by title/source label, and shows
counts. Metadata is selection context, never timed Evidence. Research lists show
25 current items per page, not an execution History. Pagination is bounded.

Lexical retrieval uses at most 32 distinct question terms, excluding a small
English function-word set; longer Chinese runs use adjacent two-character terms.
This heuristic selects candidates only. It does not infer truth, Topic membership
or authority. Queries inspect only selected Content through existing indexes.
Evidence candidate examination is capped at 100 and the output at 24 original
Evidence references and 6 admitted Intelligence interpretations. Counts disclose
word-matched candidates; truncation/omission is explicit. Exact source excerpts
over 4,000 characters are omitted whole, never silently truncated into a quote.
Sorting is score descending, Content identity, source range, Evidence identity;
Intelligence ties use Content identity and Intelligence identity.

Current admitted Intelligence may match its conclusion or its original Evidence.
All of an interpretation's citations must fit and resolve under its own Content;
otherwise omit the whole interpretation for capacity, or reject for invalid
authority. No partial citation set is called verified. Original statements,
opinions/inferences, recorded validation state and exact stances are preserved.
The result groups Evidence by Content, presents existing interpretations
separately, and identifies unanswered questions and lexical/capacity limitations.

## Identity, persistence and trusted reads

`research-lite-v1` is the frozen contract identity. Stable semantic Research id is
SHA256 of canonical UTF-8 JSON containing contract, exact trimmed question, sorted
Content scope and output language. JSON uses sorted keys, compact separators,
unescaped Unicode and forbids nonfinite numbers. Provider responses play no role.

Each explicit assembly gets a random 32-hex execution id, monotonic per-item
execution number, aware UTC assembled timestamp and canonical immutable packet.
Result identity is SHA256 of contract, Research id, execution id and packet hash.
Reruns append results and atomically update one current pointer; semantic items
do not duplicate unnecessarily. Different output languages are different
semantic items. The execution number is internal pointer-integrity data, not a
version timeline or user-facing revision feature.

Migration **031** adds separate `research_items` and `research_results`. Composite
deferred FK binds the current pointer to its own Research; result execution ids
and per-item numbers are unique. Result update/delete and semantic identity edits
are forbidden by triggers. Creation, source reads, append and current pointer
update share one `BEGIN IMMEDIATE` transaction. No other domain is written.

Read uses the explicit current pointer and rejects missing/cross-item/regressed
pointers; it never falls back to an older row to hide corruption. Strict contract,
canonical JSON, semantic/result/execution identity, language, timestamps, scope,
source-owned excerpts, ranges, hashes and every citation are reverified. Scope
titles are frozen contextual labels; later metadata refresh does not invalidate
Evidence. Missing/unavailable source authority cannot be silently dropped while
the packet remains verified. Intelligence snapshots use an explicitly recorded
revision reader: existing admission history, dependency graph, Evidence, source
membership and exact card hash are checked even after a later current revision.
The recorded state is not presented as today's current state. Newer Intelligence
is reached through existing source navigation.

## Availability, language, API and restore

Production Research capability is **DETERMINISTIC_LIBRARY_PACKET**.
`ASSEMBLED`, `EVIDENCE_AVAILABLE`/`INSUFFICIENT_MATERIAL`, provenance `VERIFIED`,
and `UNSUPPORTED_MODEL_SYNTHESIS` are separate facts. Verified provenance means
references resolve, not that every quoted claim is objectively true. No model is
qualified for Research; Deep Analysis qualification/consent grants no Research
permission. There is no provider import/dispatch, cost, cloud consent piggyback,
generic router or hidden web fallback.

`POST /api/v1/research` takes only question and Content ids. Configured output
language is captured server-side. GET collection, scope candidates, capability
and a semantic-id current result complete the local flow. Invalid question,
empty/invalid/missing scope, absent result, source authority unavailable,
corrupt saved result and execution/access failure have stable machine codes.
All UI states and controls are localized zh-CN/en; backend English diagnostics
are never shown. Source Evidence and existing interpretations retain their
original languages, while UI language and output language remain separate.
Research produces no translated Evidence or generated synthesis prose.

Backup/Restore covers both Research tables plus underlying provenance tables.
The packaged migration's exact tables/indexes/constraints/triggers are checked;
all executions, contiguous numbers, current pointers, canonical packets and
source references are verified on backup and staged restore before activation.
Invalid archives preserve current valid database/DATA bytes. Valid restored
Research remains readable after restart. Exact-schema compatibility advances
to **31**: schema-30 archives are incompatible with this build. No archive
migration framework is introduced. Historical migrations/checksums, including
reserved 029 and accepted 030, are unchanged.

## Reuse and deferrals

DIRECT: existing Python sqlite3/hashlib/json/uuid/datetime/re/importlib.resources,
approved Pydantic, React, API client, workspace styling, Evidence authority and
backup staging. ADAPT: Intelligence card verification and append-safe storage
patterns. No new dependency, lockfile/toolchain change or third-party copied code.

Phase 5 may add immutable user-visible Research revisions and History against
these stable identities and append-safe packets. Phase 6 may add Diff. Neither
timeline, old-execution read API, comparison, derived Diff, automatic historical
comparison, Research export nor promotion is implemented in Phase 4.
