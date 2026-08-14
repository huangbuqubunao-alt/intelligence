# TASK-016C Phase B Handoff Checklist

## Baseline and ancestry

- [ ] Accepted design `c547b7c…` is an ancestor.
- [ ] Accepted Phase A implementation `e8ccc2d…` is an ancestor.
- [ ] Phase A evidence `cbbe398e…` is the direct predecessor of the Phase B implementation commit.
- [ ] No squash, rebase, or history rewrite occurred.
- [ ] Phase B has exactly one implementation commit.

## Scope

- [ ] Diff is limited to `quality.py`, Phase B tests, and a justified minimal `domain.py` change.
- [ ] No scoring, Ollama, state, runtime, persistence, cache, DB, migration, ProviderCall,
      H1/H2, attestation, finalizer, filesystem, repair, TASK-016B, Cloud, Router, Weekly, or
      later-phase change exists.
- [ ] No dependency, lockfile, dictionary, NLP, token, semantic, fuzzy, POS/dependency,
      stemming, casefold, or normalization change exists.

## Gate review

- [ ] Only `EMPTY_CONTENT`, `CONTROL_CHARACTER_INVALID`, and `EXACT_REPETITION` reject.
- [ ] Gate never returns `PASS` and has no Judge/LLM/Ollama/network/persistence side effect.
- [ ] Raw control scan precedes repetition normalization.
- [ ] LF/TAB are accepted; other `Cc`, NULL, ZWSP, and BOM reject.
- [ ] Repetition is reason-only, ASCII-trimmed, LF-split, exact-empty-filtered, and adjacent
      exact code-point equality.
- [ ] Identifier/entity/technical phrases continue without Gate classification.

## TDD and mutation sensitivity

- [ ] RED evidence predates GREEN implementation.
- [ ] Tests kill removal of control validation.
- [ ] Tests kill fuzzy repetition behavior.
- [ ] Tests kill lowercase/casefold normalization.
- [ ] Tests kill removal of exact-empty filtering.

## Required gates

- [ ] `uv lock --check`
- [ ] `uv sync --locked --offline`
- [ ] Focused Phase B pytest
- [ ] Full pytest
- [ ] mypy
- [ ] Ruff
- [ ] `git diff --check`
- [ ] Final tracked worktree clean.

## Independent reviewer verdict

- Verdict: `<APPROVE PHASE B | REQUEST CHANGES>`
- P0:
- P1:
- P2:
- P3:
- Evidence commit:
- Remaining risks:
- Decision needed:
