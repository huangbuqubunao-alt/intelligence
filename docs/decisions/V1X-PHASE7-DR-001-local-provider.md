# V1X-PHASE7-DR-001: Local source snapshots in unified Following and Content

Status: Accepted for the isolated Phase 7 branch under the owner’s Phase 7 goal.
Date: 2026-10-03.
Baseline: local main `08d62d8cb459a7d157f9c4a4c87cf23a3209d4b8`, schema 31.

## Provider audit and reuse

| Existing boundary | Classification | Phase 7 disposition |
| --- | --- | --- |
| `SourceProvider.discover(ChannelRef, DiscoveryCursor)` | ADAPT | Keep the YouTube discovery contract. Explicit Local file admission is a provider capability, not channel discovery. |
| `source_subscriptions` and `source_video_links` | REUSE / ADAPT | One `LOCAL_LIBRARY` Following collection with explicit `LOCAL` provider; link every imported Content to it. |
| `videos`, Artifact DATA storage, current Summary pointers | REUSE / ADAPT | Retain the existing Content repository and Summary authority. Add provider metadata without rewriting YouTube ingestion. |
| Mandatory legacy `channel_id` | ADAPT | Use the Local collection identity internally; expose no invented channel/creator or URL. |
| Timed transcripts, durable Evidence bindings | REUSE / ADAPT | Preserve timed semantics and dependency guards; extend the same Evidence table with exact text ranges. |
| Research Lite / History / Diff | REUSE / ADAPT | Preserve old YouTube packet serialization and identities; add Local provenance and locator presentation. |
| Intelligence reader and Topic admission | REUSE / ADAPT | Keep sealed revision and dependency admission; reverify Local immutable source material. |
| Knowledge Delta | REUSE | Ordinary Content completion; no Local delta category. |
| Archive DATA backup / staged pair restore | REUSE / ADAPT | Include registered immutable source artifacts and verify new source schema and authority before activation. |
| `providers/whisper.py`, existing `mlx-whisper` dependency | ADAPT | Existing executor contract returns untimed text and has no provisioned production offline executor. Do not silently download weights or fabricate timestamps. |
| Demo Local Content in `frontend/src/demo-v1` | DEMO-ONLY | Remains demo; not imported into production. |
| Historical shell transcription / typed absolute paths | OBSOLETE for production UX | Browser File selection provides selected bytes; no user shell configuration is product authority. |
| Live paths, mutable files, filename/mtime identity, untimed media quotes as timed Evidence | UNSAFE | Never used as source authority. |

## Architecture and import contract

Local is the first production non-YouTube source. The unified flow is Provider →
Following → Content → source snapshot / canonical text or transcript → Summary →
Evidence → Intelligence → Topic / Research. No LocalSummary, LocalEvidence,
LocalResearch or new navigation destination exists.

Following → Add Source → Local files → native browser/system file picker → select
one or more files → Confirm import. The picker uses a native `input[type=file]`
with an exact extension allowlist, multiple selection and no directory selection.
The browser sends File bytes, never an original filesystem path. Headless E2E
uses the File adapter and real HTTP/SQLite/storage underneath; the owner’s actual
OS dialog interaction remains an honest manual interaction check.

`POST /api/v1/local/imports?filename=<encoded basename>` accepts selected bytes
as `application/octet-stream`. It returns 201 for new admission, 200 for a verified
duplicate, or a stable rejection code. Existing loopback/origin protection remains.
One upload may be processing at a time; oversized text is rejected before body
allocation, uploads have a read timeout, and incomplete bodies are rejected.
The UI imports at most 20 selected files sequentially and reports each outcome.

Formats are exactly TXT, MD, MP3, M4A, WAV, MP4, MOV and M4V. Text is at most
2 MiB; media is at most 64 MiB and two hours. MIME/extension impostors fail
strict UTF-8 or bounded ffprobe container/stream validation. Duplicate lookup
cannot bypass container/extension validation. Missing ffprobe rejects media
validation truthfully; text import remains available.

## Immutable source and identity

Import is a snapshot. The original remains user-owned and is never changed,
moved, renamed, deleted or given a sidecar. Managed immutable bytes are stored
under existing DATA Artifact storage. Private temporary inodes are fully written
and fsynced before atomic no-overwrite publication. Snapshot paths are derived
from a SHA-256 digest, not the selected filename or path.

Content identity is `local-<full SHA-256 of original bytes>`; provider source
identity is `sha256:<digest>` under the versioned snapshot contract. Original
bytes and original UTF-8 text remain exact, including BOM, CRLF and Markdown.
The canonical processing text has its own hash. Filename is bounded sanitized
presentation metadata only. No absolute selected path is retained, returned,
logged, exported or used in Research/Evidence identity. Provider identities cannot
be reassigned after admission.

Identical supported bytes resolve to the existing verified Content and retain
its first-import display metadata. TXT/MD and matching video containers may
share the same snapshot identity; a mismatched audio container is rejected.
Changed bytes produce a new Content identity. Deleting, moving or editing the
original after import cannot rewrite historical authority. A crash before READY
leaves an explicit imported state and a subsequent identical import safely
resumes the same snapshot. Content/snapshot admission and READY/Evidence
promotion have atomic SQLite transactions.

The native adapter test seam opens an explicitly selected symlink target once,
reads one bounded regular descriptor, and rejects in-place mutation during
reading. Replacing the selected symlink cannot redirect that open descriptor.
Managed source authority never follows symlinks in DATA paths. No filesystem
crawl, automatic import, folder watch, remote URL or background file monitoring
exists.

## Text, media and Evidence

TXT/MD accepts strict UTF-8 only; binary control data, malformed UTF-8, empty
material and replacement-character corruption are rejected. No guessed legacy
encoding is used. Text has no timestamps. `TEXT_RANGE` Evidence uses half-open
Unicode code-point offsets into exact canonical text, plus derived inclusive
line ranges for display. Ordinary text keeps line-level excerpts; highly
fragmented input uses exact bounded windows to avoid unbounded Evidence rows.
Every excerpt, range identity, Content ownership, source hash, canonical hash
and artifact membership is recomputed at trusted read time.

Media is validated locally with bounded ffprobe, file/pipe protocols only,
forced MP3/WAV/MOV demuxers (no playlist autodetection), external QuickTime data
references disabled, allocation/probe bounds and a
20-second timeout. The existing repository has an MLX Whisper adapter but no
provisioned production offline executor with authoritative segment timestamps.
Consequently normal media imports retain the snapshot and authoritative duration
with `TRANSCRIPTION_UNAVAILABLE`. This is a usable library item, not a fake
transcript or Summary. A provided offline adapter must supply bounded ordered
nonoverlapping real cues, language and provenance. Failure is explicit
`TRANSCRIPTION_FAILED`, with no trusted invented result. No network/model/cloud
call, credential, weight download or paid service is required.

Timed Local media uses the existing `TIMED_MEDIA` Evidence meaning and cue
binding. A managed immutable JSON provenance artifact binds source bytes,
canonical text, full timed transcript hash, language, duration and transcriber
identity. Restart and restore verify that envelope as well as the original
snapshot and cue/text hashes. Text ranges extend the same Evidence table;
YouTube identity, timed ranges, availability protection, immutability and
same-Content ownership remain authoritative.

## Downstream compatibility

A provider-neutral deterministic extractive adapter writes the existing
AnalysisResult Artifact and normal current Summary pointer. Its exact original
excerpts cite durable Evidence; the UI identifies them as source excerpts with
no model interpretation or translation. No separate Local Summary domain is
introduced. Untimed text does not enter timestamp-specific model contracts.

Fixture-only mixed YouTube/Local SYNTHESIS revisions must provide the exact
existing Evidence dependency set. The reader verifies each Local source;
provenance resolves each citation to its own Content/provider. Topic admission
uses the same sealed current revision and explicit association rules, never a
filename-derived Topic. No new multi-Content Distillation card contract is
invented. Timed Local media fits existing DA authority in offline fixtures;
production DA execution remains NONE, with no qualification or model calls.

Research selects Local under the same selected-Content scope. Exact text range
or timed Evidence retains provider provenance. Mixed-source deterministic
packets, restart, history and derived comparison use existing Research
contracts. Historical YouTube packet serialization is unchanged. Local Content
completion participates normally in Knowledge Delta. Local material is blocked
from YouTube manual ingestion and external/cloud Intelligence routes.

## Deletion, backup and migration

No new Content deletion UI or filesystem garbage collector is added. Existing
logical availability/dependency rules continue to govern removal. Managed source
snapshots are long-lived and retained with historical references; original user
files are never touched. An unavailable source or current Summary that cannot
be reverified makes backup fail closed, rather than producing a falsely complete
archive. Future physical snapshot removal requires dependency impact handling.

Existing archive DATA support includes full text, media, canonical transcript,
provenance envelope, Summary and other registered artifacts. It never uses a
DB-only Local backup. This is practical because per-import media is bounded at
64 MiB; existing archive/member/DATA-file/expanded-total limits remain
512 MiB / 512 MiB / 256 MiB / 2 GiB. A library exceeding archive bounds gets an explicit rejected backup,
not a silently incomplete backup. Media is restored only when its snapshot is
present and verified; no restored original user path is claimed.

Restore checks ZIP paths, duplicates, symlinks, expansion limits, manifest
hashes, packaged source constraints/triggers, complete Local Evidence authority,
Summary and Research authority before replacing the staged database/DATA pair.
Corrupt sources, excerpts, cue times and missing authority guards fail safely.
Existing version-specific archive compatibility remains: this branch creates
and accepts schema-32 archives. A schema-31 archive requires its matching
accepted application for restoration, then normal database upgrade; it is not
silently treated as a schema-32 archive. Live schema-31 databases upgrade normally.

One coherent migration, `032_add_source_provider_authority.sql`, upgrades
schema 31 to 32. All historical migration checksums stay unchanged; ordinal 029
is absent. Table rebuilds use foreign keys disabled only during the atomic
migration transaction, legacy rename behavior to preserve referring contracts,
then foreign-key verification before commit and restored connection pragmas.
The rebuilt Evidence table preserves every original protection trigger. Strict
schema/history, SQLite quick/integrity/foreign-key checks remain required.

## Deferred scope

No PDF, image/OCR, watched folder, Drive, Dropbox, iCloud, Bilibili, X, Douyin,
Xiaohongshu, extension, cloud upload, scraping, account or synchronization.
A provisioned production offline transcription executor and text-compatible DA
model contracts are future work, never represented as available here. The next
provider needs the same Following/Content/artifact/locator authority; it must
not introduce another parallel Evidence or Research subsystem.
