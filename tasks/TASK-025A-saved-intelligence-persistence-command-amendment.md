# TASK-025A — Saved Intelligence Persistence & Command Amendment

Status: AUTHORIZED by Product Owner. START_ANCHOR:
`eb002b64649495d9b2567ade13b08117a877118f` (approved TASK-025).
Branch/worktree: `codex/task-025a-saved-intelligence`,
`/Users/hua/Documents/yia-worktrees/task-025a-saved-intelligence`.
Serial predecessor: TASK-025; successor: TASK-026 after separate authorization.

## Purpose and ownership

TASK-026 correctly blocked: frozen V1 Save Intelligence lacked a persisted
relation and application commands. Save remains required; this amendment fills
ownership without expanding Product Spec semantics. Own m014 (v013→v014),
minimal repository/domain/service, bounded local API commands/read, tests,
version gates and authority/handoff docs. Reuse DIRECT Python sqlite3,
dataclasses and existing approved dependencies; ADAPT existing repository/API
patterns; REUSE TASK-019 reader without modification. No new dependency.

## Minimum contract

- One current local relation keyed by exact stable `intelligence_id`; no
  user/account architecture, copied content, revision snapshot, folders or tags.
- `saved_at` is backend UTC time of transition from unsaved to saved. Duplicate
  Save preserves it; Unsave then Save creates a new save time. It never becomes
  an Intelligence event/revision timestamp.
- Typed `SaveIntelligence` and `UnsaveIntelligence` take only target identity.
  Save validates current legal identity through `AuthoritativeIntelligenceReader`.
  All classified kinds and readable lifecycle states (including DISPUTED) are
  eligible. Unreadable targets cannot newly be saved. Unsave is a set removal:
  repeated/absent IDs are a no-op, including later-unavailable saved targets.
- Save/Unsave are idempotent state-setting commands, not a replay log across
  intervening opposite actions. Database uniqueness handles concurrent Save.
- Saved listing uses bounded keyset pagination ordered by saved_at descending,
  then exact ID; every entry resolves the current TASK-019 verified read.
  Legal details remain at the existing Intelligence detail endpoint. No raw
  card payload or trusted flag is accepted from clients.
- Rejected reads retain only saved identity/time and an UNAVAILABLE marker;
  no current card/claim/state is reconstructed from raw rows. Saving never
  upgrades RUMOR, PREDICTION, OPINION, SYSTEM_INFERENCE or DISPUTED.
- m014 creates empty state, FK RESTRICT to Intelligence, no cascade and no
  historical content changes. Unsave deletes only the organization relation.
- No Preference/Feedback, Topic/pin, Source policy, Evidence, revision,
  Weekly, ledger, model/provider or trust mutation. No second trusted type.

## Acceptance and stop

Strict TDD: migration fresh/v013 upgrade/all prior data preserved, rollback,
package discovery, no fabricated saves/m015; Save/Unsave uniqueness/idempotency,
backend time, current revision following, all kinds/dispute preservation,
unavailable/invalidated targets, forged inputs/raw-row trust denied, concurrency,
and zero effects on every prior domain. Run focused and all requested prior
regressions, full pytest, mypy src, Ruff, offline build, packaged-runtime checks,
diff check and canonical scanner (EXIT 1, 11 accepted fixtures, 0 new; not PASS).
Independent adversarial review → fix all P0/P1 → retest → re-review.

Stop for trust/domain reinterpretation, m015, real provider/Deep Analysis,
unknown dirty work, unresolved scanner finding, or unclosable P0/P1. No UI,
TASK-026 implementation, TASK-027, V2, push/merge/tag/release/history rewrite.
Handoff records evidence, exact commits, review and whether TASK-026 can now
consume legal Save/Saved/Unsave contracts. Stop after TASK-025A closeout.
