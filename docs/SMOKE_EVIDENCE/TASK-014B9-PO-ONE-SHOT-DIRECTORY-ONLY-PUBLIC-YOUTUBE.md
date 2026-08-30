# TASK-014B9 product-owner one-shot directory-only evidence

- Fresh authorization baseline: `d75988aaa47f34e419119181a31245ab2e143c88`.
- Historical authorization/execution: `e975ff4` is consumed; preserved unmerged evidence
  `bd770ef` records `CONTENT_UNAVAILABLE` with counts `1/1/0`.
- New authorization: the separately recorded PO package authorized one semantic attempt only.
- Sample: `eIho2S0ZahI`, reused only under the new authorization; no substitution occurred.
- Timeout: the existing 30-second network-call timeout. No product retry occurred. The locked
  yt-dlp runtime retains its documented extractor retry default for known extractor errors;
  that transport behavior is not another B9 semantic attempt.
- Public operation: one directory-only invocation; metadata/enumerate/body counts were
  `1/1/0`; process exit was `1`.
- Result: `FAIL` at subtitle-directory contract validation with fixed `INVALID_RESPONSE`.
  Approved safe diagnostics were `directory_shape_unknown`, `directory_origin_mapping`, and
  `directory_fingerprint_unknown`; no body was read.
- Directory boundary: a new nonexistent temporary smoke root was used. Only its expected
  local smoke artifacts were created; no repository file changed. The created root was moved
  to Trash after relative-only inspection.
- Security baseline: 11 existing `api-key` findings in the two TASK-016 test files; no B9
  scanner policy, allowlist, or test exemption changed.
- Deterministic validation: subtitle/smoke focused tests `149 passed`; scanner regression
  tests `20 passed`; combined focused tests `169 passed`; full pytest `1910 passed, 1 warning`;
  `uv run mypy src` and Ruff passed. Repository-wide mypy remains the documented non-regression
  baseline of `1019` errors in `44` files. Pre- and post-B9 security scans both reported only
  the same 11 TASK-016 findings and exited `1`; `git diff --check` passed.
- Qualification interpretation: application behavior is `CORRECT` and fail-closed; this
  evidence is not a release approval or proof of general public-provider compatibility.
- New authorization status: `CONSUMED`; semantic retries and post-start substitutions: `0`.
- Independent adversarial review: `APPROVE`; no evidence of historical authorization reuse,
  a second semantic attempt, sample substitution, timeout escalation, unsafe path disclosure,
  scanner weakening, or TASK-014B11/TASK-016 change (`P0=0`, implementation-critical `P1=0`,
  `P2=0`).
