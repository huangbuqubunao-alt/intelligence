# TASK-014B9 final named-sample one-shot qualification

- Authorization: distinct Product Owner final named-sample one-shot authorization, 2026-08-31; consumed by
  this single invocation. Contract baseline: ADR-022 `7f0915944a64879785e53a1993ddf0e6897e3350`; nomination
  baseline: `e881694af7fa7c023b849a30cabb5243bce2aec6`; clean execution baseline: the nomination commit.
- Historical chronology is preserved: `eIho2S0ZahI` remains retired and not used; its consumed executions
  remain `CONTENT_UNAVAILABLE` and `INVALID_RESPONSE`, both at `1/1/0`.
- Fixed replacement sample: `5MWT_doo68k`; no discovery, substitution, fallback, iteration, or historical-ID
  reuse occurred.
- Canonical live entrypoint: the committed `smoke-public-subtitles --directory-only` command with the fixed
  30-second timeout and a newly created, previously nonexistent smoke root. One semantic invocation returned
  exit `0`, `metadata=1`, `enumerate=1`, `read=0`, and safe result `OK`.
- Accounting: authorized/actual semantic attempts `1/1`; semantic retries `0`; application transport retry
  loop `0`; observed transport retries `0`; substitutions `0`; fallback `NO`; timeout escalation `0`.
- Directory-only result: `PASS`. The safe JSONL summary recorded one target, zero failures, and the same
  `1/1/0` counts. B11 validation and diagnostic-secrecy boundaries remained in force; no body was read.
- Filesystem effect: only the fresh smoke root's state file, empty data/test-vault directories, and one safe
  JSONL log were created. All were individually removed after the safe-summary inspection; no retained public
  body, raw response, URL, title, absolute path, credential, or user data exists in this evidence.
- Security comparison: before and after scans each exited `1` solely for the same eleven pre-existing
  TASK-016 `api-key` test-fixture findings in two tracked test files. New TASK-014B9 findings: `0`; scanner
  policy was unchanged.
- Deterministic validation: B9/safe-directory/provider focused tests `149 passed`; scanner regression `20
  passed`; full pytest `1910 passed, 1 warning`; `uv run mypy src` passed for 40 source files; Ruff and
  `git diff --check` passed. Repository-wide mypy remains non-regression evidence at `1019` errors in `44`
  files.
- Result: `PASS`. TASK-014B9 is `QUALIFIED / CLOSED`; this does not make TASK-014 release-ready or grant
  release approval. B11 and TASK-016 are unchanged.
