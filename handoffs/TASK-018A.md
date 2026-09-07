# TASK-018A Handoff — Persisted Claim Classification Amendment

## Outcome

- START_HEAD: `7d89f5965a0c87d599e48ba72b887b3322ef4c17`
- Product Owner decision applied: persisted claim classification belongs to an
  immutable `IntelligenceRevision`, separate from lifecycle state.
- TASK-018 remains closed and `006_add_intelligence_domain.sql` is byte-for-byte
  unchanged.
- TASK-018A adds only `007_add_intelligence_claim_classification.sql`; fresh
  databases now reach `PRAGMA user_version = 7`.

## Durable contract

`IntelligenceClaimKind` contains `FACT`, `EVIDENCE_BACKED_STATEMENT`,
`OPINION`, `PREDICTION`, `RUMOR`, and `SYSTEM_INFERENCE`. `UNCLASSIFIED` is
available only to represent migrated m006 rows. m007 gives legacy rows that
sentinel without interpreting their text, evidence role, lifecycle, or hash.

New repository writes require a real finite enum and reject `UNCLASSIFIED`.
The database CHECK rejects arbitrary values, while a m007 insert trigger also
rejects explicit or defaulted new `UNCLASSIFIED`. The existing m006 revision
immutability trigger protects the new column as well. Classification itself
does not grant admission, confirmation, or trusted-read authority.

## Planning amendment

TASK-018A exclusively owns m007. Future owners shift one slot: TASK-020 m008,
TASK-021 m009, TASK-022 m010, TASK-023 m011, and TASK-025 m012. TASK-019 owns
no migration and must start from this approved correction anchor. It must
reject legacy `UNCLASSIFIED` in its future trusted reader.

## Verification evidence

- Focused persistence and regression suite: `133 passed`.
- Full suite: `1988 passed, 1 skipped, 1 existing Pydantic serializer warning`.
- `uv run --offline mypy src`: 45 source files, no issues.
- `uv run --offline ruff check .`: passed.
- `uv build --offline`: wheel and sdist built (known uv build-system version
  warning only); both archives contain m006 and m007 migration resources.
- `git diff --check`: passed.
- Scanner not run: the frozen task graph reserves its canonical scanner gate
  for later integration checkpoints; TASK-018A has no credential/provider or
  external-execution change.

## Adversarial review and re-review

The test suite attacks arbitrary, explicit sentinel, and omitted/defaulted
claim kinds through raw SQL; production repository writes with forged values;
in-place mutation; migration rollback; and old-row semantic guessing. It also
proves FACT does not set lifecycle confirmation and SYSTEM_INFERENCE survives
as a distinct finite value. Re-review confirms P0=0, P1=0, P2=0. Frozen
scoring, dispatch/AMBIGUOUS, credentials, Note/Weekly authority, and Deep
Analysis are unchanged. No TASK-019/TASK-020 implementation exists here.
