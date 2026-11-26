# V1.x Advanced Intelligence milestone closure

Closure date: 2026-10-03. This closes the accepted V1.x capability sequence into a
local mainline candidate. It is not Phase 7, a main update, or a release.

## Candidate and history

Repository: `/Users/developer/youtube-intel`.
Worktree: `/Users/developer/Documents/yia-worktrees/v1x-milestone-closure`.
Branch: `chatgpt/v1x-milestone-closure`.
Accepted starting baseline: `b7aa90fd788150acb61f3f258d8353b5ec33edef`.
Discovered local main: `41233ee9aac647c99ef3c847130ef06624bbeaa5`.
Default tracking ref: `origin/HEAD -> origin/main`, locally recorded at
`22d138e8c20d6ef7be59f89907d61bf83bd5aa9e`; no fetch or push was performed.

CASE A applies: main is the merge base and an ancestor of the exact V1.x baseline;
main-only commits: zero; V1.x-only commits relative to local main: 170. The tracked
origin/main is also an ancestor (zero/49 divergence). No merge or conflict resolution
was necessary. Both main histories are preserved by ancestry, not reconstructed.
The original checkout remains `rc4/usability-test`, clean. Existing local tags are
historical RC/phase tags; none was moved or created.

Accepted ancestors preserved: Phase 1B `432f085`, Phase 1C `72950a5`, Phase 2
`b9362fb`, Phase 3 `795275c`, integration `ba9f27f`, Phase 4 `22ea84a`, Phase 5
`15f7203`, Phase 6 `b7aa90f`. Full SHAs and topology are recorded in
[the topology evidence](../../handoffs/V1X-CLOSURE-TOPOLOGY.json).
The final locally committed HEAD is identified by the Git branch and final report;
this record does not attempt to embed its own commit hash.

## Accepted capability and authority

- Deep Analysis remains Content-only with five roles. Only trusted Phase 1B
  durable same-Content Evidence/results are authoritative after restart. Phase 1A
  rows remain transitional, untrusted and not publishable. Candidate Evidence
  does not become durable authority by configuration or UI state.
- Production DA execution route is **NONE**. Configuration, reachability,
  qualification and production eligibility remain separate. Settings cannot mint
  qualification. Exact per-run cloud consent, selected-Evidence-only default
  egress, truthful cost and no silent fallback/paid retry remain unchanged.
- Obsidian is explicit one-way publication of trusted DA, with SQLite authority,
  stable semantic note identity and provenance-only result identity. No import,
  invented wikilinks or vault files in core backup.
- Home Knowledge Delta remains a deterministic seven-day derived view: no model,
  persistence, watermark or “since last viewed” semantics.
- Research production mode is **DETERMINISTIC_LIBRARY_PACKET**: explicit selected
  Content, library-first bounded matching, stable semantic identity, immutable
  execution/revision and atomic current pointer. No model/cloud/web exploration.
- History reads trusted immutable original packets. Diff derives deterministic
  comparisons from two trusted snapshots; it is not persisted authority.

No generic router, qualification run, new provider, Research synthesis/projection,
cloud sync, accounts, graph/RAG/chat, persisted Delta/Diff or Phase 7 was added.

## M13 disposition and remediation

[The complete 35-entry audit](V1X_M13_REMEDIATION_AUDIT.md) classifies actual diffs
and untracked contents, not filenames. Counts: 3 SUPERSEDED, 5 STILL_REQUIRED,
2 CONFLICTS_WITH_NEW_AUTHORITY, 25 TEST-DOC-ONLY, 0 UNKNOWN.

Forward-ported compatible requirements using current authority:

- Global focus/ignore/style editing uses the existing source-policy revision
  service; Following exposes and retains actual inheritance/override modes.
  Chinese and ASCII commas are accepted. Existing caps and semantic authority
  remain unchanged; these preferences affect future checks only.
- Bounded loopback model discovery and candidate preference reuse existing model
  preferences. Neither discovery nor save qualifies/activates a route or changes
  the configured Scoring/Summary model. No live inference was performed.
- Existing reviewed Moonshot video-distillation credential configuration uses
  native macOS Keychain APIs with redacted failure, no secret in argv/files/SQLite,
  explicit deletion confirmation and separate per-execution consent. It does not
  qualify Deep Analysis. No live credential/provider was used in validation.
- A prepared private-stage launcher builds `.var/Intelligence.app`. Normal owner
  Open/Stop and optional Obsidian folder selection use a native dialog; the app
  starts the standard local runtime and built frontend in an isolated candidate
  workspace. It creates no installer, bundled dependencies, launchd service or
  public packaging. Existing dependencies/build must first be prepared by the
  engineering setup; this is not a public installation flow.

Already accepted UI/output-language separation, localization, Following
explanations and schema31 backup authority supersede old M13 work. The competing
M13 model configuration, discovery-as-qualification, hardcoded cloud qualification,
shell credential handling and duplicate persistence were rejected. Dirty M13 was
not committed, stashed, reset, cleaned, copied wholesale or merged.

Additional integrated defects found and fixed: Research scope could crash on
nullable channel metadata; PO demo DA reads returned404 instead of truthful
unqualified state; Settings success feedback disappeared on refresh; interest
validation could expose English backend prose in Chinese UI. Regression checks
cover each, retaining existing assertions and adding stronger DA-route assertions.

## Schema, backup and restore

Schema remains **31**. Packaged and applied migrations are 001–028, 030, 031.
The intentional gap at029 is accepted lineage. 030 owns durable DA Evidence;
031 owns Research items/executions/current/references. History/Diff need no
migration. Every applied checksum matches the unchanged packaged SQL. No032
was needed: preferences already have persistence and credentials are machine-local
Keychain state, outside portable product authority.

M13's uncommitted `029_add_v1_model_configuration.sql` remains only in M13,
SHA256 `583e5bcaeec9573f6d2ca6cb79fe26a65fa1c83aedc7d656d4cd611b2f6bccf3`.
It was neither imported nor renamed.

A real HTTP backup/download/stage/confirm/startup-restore cycle used isolated data
containing Content, durable Evidence, trusted DA and Research with at least three
immutable revisions. Exact post-restore API snapshots matched DA/Evidence,
Research current pointer, complete History and original revisions. Diff and Delta
recomputed identically; Obsidian republished. A corrupt ZIP was rejected with409
without changing the live database dump or authority snapshots. External vault,
Delta and Diff were absent from archive members. A separate real History restore
verified 25-row pagination, every page/order, original packets and browser source
tracing. Fresh/upgraded and restored databases pass quick_check/integrity_check
(`ok`) and foreign_key_check (empty).

## Validation and review

[The validation manifest](../../handoffs/V1X-CLOSURE-VALIDATION.json) records
commands, outcomes, evidence hashes and review disposition. Validation uses
isolated data and network/Keychain guards; no model/cloud/paid call or external
Research exploration was used.

- Backend full suite: 3,274 passed, one unchanged optional canonical-o200k-asset
  skip, two existing fixture warnings (duplicate ZIP entry and Pydantic serializer).
  Focused V1.x/authority,
  qualification/consent/cost, Obsidian/Delta/Research/History/Diff, Settings,
  Following/migrations/Backup and forward-port suite: 665 pass.
- Frontend: 166 tests pass, typecheck and production build pass.
- Real Chrome: accepted integration, Research/History and Diff each pass eight
  zh-CN/en scenarios at320/768/1024/1440px; unified owner flows pass before and
  after restore. Existing broad product smoke passes desktop/tablet, including
  onboarding, Summary/Evidence modes, Intelligence/Topic and settings. No
  unexpected console errors, external requests, overflow or seventh navigation
  destination. Native application build/open and standard local restart were
  verified; native dialog automation was unavailable, so folder-picker interaction
  and real Keychain access were not exercised. These are owner-stage checks,
  not evidence of public installation readiness.
- Ruff, strict mypy (79 source files), compileall, diff whitespace, design reference
  lint and closure/decision link/index checks pass. No dependency/lockfile change.
- Three self-reviews and fresh acceptance against main, exact V1.x baseline and
  all M13 entries found no unresolved P0/P1 or material closure P2. The accepted
  authority modules/migration SQL remain unchanged; only compatible configuration
  wiring, current UI remediations and the narrow null-metadata read fix were added.

M13 remains at `e228294f705401b0200439076c3378b78f9c9d84`, with the same35 entries.
Before/after HEAD/status, tracked-diff hash, all tracked/nonignored-untracked
file fingerprints and029 hash match. The other seven accepted source worktrees
also match. See [before](../../handoffs/V1X-CLOSURE-PRESERVATION-BEFORE.json),
[after](../../handoffs/V1X-CLOSURE-PRESERVATION-AFTER.json) and
[comparison](../../handoffs/V1X-CLOSURE-PRESERVATION-PROOF.json).

## Operational assessment

The candidate is ready for **owner dogfood continuation/recheck** in the existing
Gate A functional/private path, with unavailable DA generation explained and
previous trusted results usable. This does not fabricate seven owner days, reset
M13, or qualify the owner's actual local Summary model. The historical real
Summary INVALID_RESPONSE remains recorded; no live model run was authorized.

A limited private pilot is **not newly cleared** by this closure: complete the
owner rechecks/M13 operating evidence and separately authorize pilot use. Public
distribution is **not ready/NOT ASSESSED**: M14/Gate B was not executed, and
M12/V1.x closure is not Gate B PASS. Native signing/notarization/distribution,
public installation, real Keychain/Obsidian folder interaction and live provider
qualification are not claimed validated.

No milestone-integration blocker remains. Recommended next step: owner reviews
this clean local candidate, authorizes the actual main merge separately, then
continues real owner dogfood. Push, PR, main update and release need separate
owner authorization; none occurred in this task.
