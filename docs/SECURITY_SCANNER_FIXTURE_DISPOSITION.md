# Canonical Security Scanner Fixture Disposition — 2026-08-31

## Status

**CANONICAL SCAN: EXIT 1. FINDINGS: 11.** This is an evidence record, not a
green scan, suppression, allowlist, or approval. Technical review classifies
all eleven as intentional positive test fixtures, but the release-security
blocker remains **WAITING ON SECURITY REVIEWER / TL DISPOSITION**. No Security
Reviewer or TL approval is recorded here.

Baseline: `main@e8c00a4fecfb23d1b163a6352ca7c3a13a1eaf7a` before this
documentation-only evidence change. The unchanged command was:

```text
bash scripts/security_scan.sh
```

It returned `1` with the matrix below and no additional finding. Output carries
the scanner's redacted fingerprints, never a fixture value.

## Scanner contract and current policy

`scripts/security_scan.sh` is a `set -euo pipefail` wrapper around
`scripts/_security_scan.py`. The scanner enumerates tracked text/source files,
checks sensitive tracked-file classes and `dist/` archives, and fails closed if
enumeration, reading, parsing, or extraction fails.

- Exit `0` means `status=clean`: no blocking finding.
- Exit `1` means a blocking finding or scanner failure.
- `WARN` items are explicitly review-only; rules have no severity classes.
- All eleven records are blocking `api-key` matches.

The authoritative release evidence requires a “cleanly closed global security
scan” and says no formal release-policy closure treats a non-zero global scan
as green: [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md),
[RELEASE_BLOCKERS.md](RELEASE_BLOCKERS.md), and
[RELEASE_SIGNOFF.md](RELEASE_SIGNOFF.md). It defines neither a reviewer
exception mechanism nor an expiry/owner for one. Current policy is therefore
**D — ambiguous/no approved exception rule**, not Policy A/B/C by inference.

## Finding matrix

All records are tracked `tests/` Python files, class **B — intentional positive
test fixture**, and match a synthetic `sk-...` shape under `api-key`. The
fingerprints are scanner fingerprints, not credentials.

| # | File:line | Fingerprint | Test purpose / consumption | Runtime and artifact disposition |
| --- | --- | --- | --- | --- |
| 1 | `tests/integration/test_deep_analysis_persistence.py:195` | `d72693d06a177c8d` | `_trusted_success` injects a sentinel into an in-memory OpenAI adapter transport to create a persistence-test success. | Test-only injected callable; absent from wheel/sdist. |
| 2 | `tests/integration/test_deep_analysis_persistence.py:403` | `d72693d06a177c8d` | Proves item 1's sentinel is absent from the persisted record. | Test assertion only; absent from wheel/sdist. |
| 3 | `tests/unit/test_kimi_deep_analysis_adapter.py:128` | `5596714c56730240` | Request projection, selected evidence, timeout, and zero-retry test through `_Transport`. | In-memory `_Transport`; absent from wheel/sdist. |
| 4 | `tests/unit/test_kimi_deep_analysis_adapter.py:149` | `5596714c56730240` | First observational request-ID/usage response. | In-memory `_Transport`; absent from wheel/sdist. |
| 5 | `tests/unit/test_kimi_deep_analysis_adapter.py:150` | `5596714c56730240` | Second observational request-ID/usage response. | In-memory `_Transport`; absent from wheel/sdist. |
| 6 | `tests/unit/test_kimi_deep_analysis_adapter.py:158` | `5596714c56730240` | Fenced output remains untrusted. | In-memory `_Transport`; absent from wheel/sdist. |
| 7 | `tests/unit/test_kimi_deep_analysis_adapter.py:162` | `5596714c56730240` | Fabricated evidence remains untrusted. | In-memory `_Transport`; absent from wheel/sdist. |
| 8 | `tests/unit/test_kimi_deep_analysis_adapter.py:169` | `5596714c56730240` | Model mismatch rejects without retry. | In-memory `_Transport`; absent from wheel/sdist. |
| 9 | `tests/unit/test_kimi_deep_analysis_adapter.py:175` | `5596714c56730240` | Malformed envelope rejects without retry. | In-memory `_Transport`; absent from wheel/sdist. |
| 10 | `tests/unit/test_kimi_deep_analysis_adapter.py:194` | `5596714c56730240` | Error mapping has no SDK or semantic retry. | In-memory `_Transport`; absent from wheel/sdist. |
| 11 | `tests/unit/test_kimi_deep_analysis_adapter.py:201` | `5596714c56730240` | Sentinel is absent from adapter repr, failure repr, JSON, and dispatch-envelope surfaces. | In-memory `_Transport`; absent from wheel/sdist. |

The two synthetic literals are deliberately reused; the count is eleven scanner
locations, not eleven independent credentials. Each occurrence is tied to a
test/helper assertion rather than granted fixture status by its path alone.

## Secret, runtime, and distribution evidence

No authentication, provider call, or live-secret validation was attempted.
The only consumers supply a lambda or test-local `_Transport` callable. Both
adapters call injected `self._transport(request, credential, timeout, retries)`;
the test implementations return in-memory mappings and make no HTTP,
subprocess, filesystem credential-store, cache, database, or log call. The
persistence test explicitly asserts the sentinel is not retained in SQLite.

The values are fixed synthetic test sentinels, occur only in these two tests,
and are not environment-derived. Real API keys, tokens, passwords, credentials,
or plausible live secrets found: **0**. Production runtime, CLI, and
provider-credential reachability: **none**. The test harness may intentionally
pass a sentinel to its injected callable; that is not production reachability.

Fresh `uv build --offline` artifacts were directly inspected:

| Target | Finding test paths | Exact fixture values | `api-key` regex matches | `site-packages` / dependency wheels |
| --- | --- | --- | --- | --- |
| Wheel | no | no | 0 | no / no |
| Sdist | no | no | 0 | no / no |
| Controlled full Git source tree | yes — both tracked tests | yes | 11 canonical findings | not applicable |

Thus wheel and sdist are fixture-free, while the controlled full source tree is
not. This task does not authorize a bundle, container, installer, copied venv,
or public release.

## Regression, policy paths, and adversarial review

`uv run --offline pytest tests/scripts/test_security_scan.py` passed: **20
passed**. The suite uses isolated temporary Git fixtures to prove credential
detection, redaction, fail-closed parse/enumeration/archive handling, exact
placeholder boundaries, and non-bypass behavior. The project findings are not
a scanner blind spot.

At-most-once risk acceptance is separate: `RELEASE_BLOCKERS.md` assigns its
three crash windows to the PO. It neither grants nor replaces a Security
Reviewer/TL scanner disposition.

Because no exception rule exists, the current release posture is global-exit-0
and this blocker remains open. A future Security Reviewer/TL policy decision
could first establish and sign a finite disposition for exactly this matrix,
including controlled-source presence, scope, owner, and review trigger, while
keeping scanner exit `1` explicit. A first-class scanner/scope architecture
change is a possible future design task only; it is not authorized or
implemented here.

Adversarial review found no real secret, production/provider flow, wheel/sdist
inclusion, policy approval fabrication, scanner weakening, allowlist, fixture
change, TASK-016/B9/B11/ADR change, push, tag, or public release. Technical
review: **P0 0; release-critical technical P1 0; P2 0.**

## Required disposition

**SECURITY RELEASE BLOCKER: WAITING ON SECURITY REVIEWER / TL DISPOSITION.**
The next authorized action is: **Security Reviewer / TL approve or reject the
documented eleven-fixture release-policy disposition.** No legal or policy
approval is fabricated.
