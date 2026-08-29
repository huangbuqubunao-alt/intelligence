# TASK-016D Deep Analysis Persistence Closed-Loop Review

Review targets: implementation `4635c984ac85d15ce4b6bcc21992d753452810d9`,
provenance-integrity correction `84715a0`, plus final evidence.

## Result

`APPROVE`

- Final P0: `0`
- Final implementation-critical P1: `0`
- Implementation rounds: `1`
- Correction rounds: `1`

## Adversarial matrix

| Attack | Result |
| --- | --- |
| Forged or reconstructed runtime success write | Rejected; no row commits. |
| Raw database row as runtime trust | Impossible; reads return only `VerifiedPersistedDeepAnalysisRead`. |
| A1/A2/A3/cache/content/hash/provider/scoring/registry/policy/scope tamper | Fail-closed cache miss. |
| Persisted provenance/result identity tamper | P0 found: initially accepted. Regression test added; reader now recomputes the exact runtime-minted DACS-1 provenance object and rejects both mismatches. |
| Provenance class used as scoring request identity | Rejected by persisted canonical request-hash binding. |
| Floating profile cache reuse | Rejected; floating is audit-only/cache-ineligible. |
| Same cache identity, different content | SQLite partial unique index rejects it. |
| Provider request ID / usage in cache semantics | Excluded from semantic cache fields. |
| Secret sentinel or unselected transcript leakage | Absent from persisted row coverage. |
| Migration data/version integrity | Existing migration, history, WAL/FK, and doctor tests pass. |
| Provider/network/credential invocation | None made or introduced. |
| TASK-016B/C or 016E/F change | None. |
| Revalidation-material retention | The sole cache entry and its protected revalidation material are the same app-only row; no separate artifact path can outlive the entry. §11 specifies no independent TTL, so none was invented. |

The review added regression coverage for provenance identity tampering, the
model-class/cache-eligibility binding, and the same-key conflicting-content
rule. The P0 was corrected in `84715a0`; no implementation-critical finding
remained after the independent re-run.

## Validation evidence

Focused persistence/migration/Deep Analysis tests: `146 passed`. Full pytest:
`1873 passed, 1 existing warning`. Target test mypy and `uv run mypy src` pass;
Ruff and `git diff --check` pass. `uv run mypy .` retains the historical
`1019 errors / 44 files` baseline with no TASK-016D error.

## Required release gate

OpenAI live qualification remains `PENDING / CREDENTIAL BLOCKED`.
`OPENAI LIVE QUALIFICATION 2/2` remains required before real-cloud release or
smoke. No live request was made.
