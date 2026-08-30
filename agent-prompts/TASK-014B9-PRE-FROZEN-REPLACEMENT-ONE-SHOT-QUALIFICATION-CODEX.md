# TASK-014B9 pre-frozen replacement one-shot qualification package

## Status and authority

**CONSUMED / PRESERVED.** The Product Owner separately authorized this exact package, which completed its one
live qualification successfully. Its result is recorded in
`docs/SMOKE_EVIDENCE/TASK-014B9-FINAL-NAMED-SAMPLE-QUALIFICATION.md`. This historical package authorizes no
discovery, fallback, retry, source change, merge, push, or tag.

## Frozen scope

- Task: `TASK-014B9` replacement public-sample directory-only qualification.
- Contract baseline: ADR-022 `7f0915944a64879785e53a1993ddf0e6897e3350`; preserved prior evidence through
  `d8a7f2aee2b8683e6a75bdea0b39243b26fe0b74`; nomination evidence:
  `docs/SMOKE_EVIDENCE/TASK-014B9-REPLACEMENT-SAMPLE-NOMINATION.md`.
- Sample: `5MWT_doo68k` — the only pre-frozen replacement sample. It is eligible for qualification, not
  qualified. No sample discovery or selection is permitted during future execution.
- Required source: this branch at the clean commit that records this package; only this worktree's absolute
  `.venv/bin/youtube-intel` launcher may be used after the required locked offline preflight.
- Reuse decision: `DIRECT` — integrated B4 directory-only smoke, B5 safe summary, ADR-017 through ADR-022,
  B11 safe-directory contract, and locked dependencies. No product-code or dependency change is authorized.

## One-shot execution boundary

Before a future live call, require a clean worktree, `uv lock --check`, `uv sync --locked --offline`, a second
`uv lock --check`, launcher mapping verification, a fresh parent directory, and a nonexistent `smoke-root`
child. Freeze the current security baseline before execution.

The future authorization permits exactly one command:

```text
ABSOLUTE_EXECUTION_WORKTREE/.venv/bin/youtube-intel smoke-public-subtitles --directory-only --temporary-root ABSOLUTE_NEW_PARENT/smoke-root --video-id=5MWT_doo68k
```

- Semantic attempts: `1`; semantic retries: `0`; post-start substitutions: `0`; fallback: `NO`; timeout:
  existing fixed 30-second network-call timeout; timeout escalation: `0`.
- Required operation counts: metadata=`1`, subtitle-directory enumerate=`1`, body read=`0`.
- No authentication, Cookie, account data, credential, `.env`, media download, model, paid service, Vault,
  user data, or additional product command is permitted.
- B11 directory validation, restricted-key rejection, traversal/escape protection, and safe diagnostic secrecy
  remain mandatory. `INVALID_RESPONSE` remains fail-closed; it is never a pass.

## Results, evidence, and validation

A nonzero exit, wrong operation count, directory-contract failure, leak, or external failure consumes the
future authorization and stops execution. It does not authorize a retry, a different sample, a timeout change,
or a source fix followed by another call.

Record only approved safe summary fields, safe relative filesystem effects, cleanup, authorization accounting,
and validation. Do not retain raw responses, URLs, titles, subtitle content, exception text, absolute paths,
credentials, or user data. Then run B9/TASK-014/safe-directory/provider focused tests, scanner regression,
the repository security scan, full pytest, `uv run mypy src`, repository-wide mypy as non-regression evidence,
Ruff, `git diff --check`, and independent adversarial review. TASK-014B9 may close only on the exact B9 pass
criteria; it is never a release approval by itself.
