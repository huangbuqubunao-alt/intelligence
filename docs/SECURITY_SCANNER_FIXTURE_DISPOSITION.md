# Canonical Security Scanner Fixture Disposition — 2026-08-31

## Status

**CANONICAL SCAN: EXIT 1. FINDINGS: 11. CLASSIFICATION: 11 INTENTIONAL POSITIVE
TEST FIXTURES.** The scanner's technical result remains non-zero. It is not a
green scan, global bypass, suppression, or allowlist.

**RELEASE DISPOSITION: ACCEPTED FINITE PO/TL RELEASE-POLICY EXCEPTION.** The
Product Owner / Tech Lead explicit policy disposition applies only to the exact
eleven documented findings at `main@5e15d62`. It resolves the **security
technical release blocker for the current controlled private source/wheel/sdist
posture**. It does not constitute a final-release GO signature, an independent
Security Reviewer signature, legal approval, or authorization for a wider
distribution form.

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

The Product Owner / Tech Lead disposition supplied for this record establishes
the finite exception described below. It does not change scanner exit semantics:
the result remains exit `1`, never “security scan PASS” or “global scan clean.”
The repository's separate final-signature and independent Security Reviewer
requirements remain governed by [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md),
[RELEASE_BLOCKERS.md](RELEASE_BLOCKERS.md), and
[RELEASE_SIGNOFF.md](RELEASE_SIGNOFF.md).

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
not. The finite exception is limited to the current controlled private
source/wheel/sdist posture; it does not authorize public open-source or package
index release, bundle, container, installer, copied venv, or vendored
environment distribution.

## Regression, policy paths, and adversarial review

`uv run --offline pytest tests/scripts/test_security_scan.py` passed: **20
passed**. The suite uses isolated temporary Git fixtures to prove credential
detection, redaction, fail-closed parse/enumeration/archive handling, exact
placeholder boundaries, and non-bypass behavior. The project findings are not
a scanner blind spot.

At-most-once risk acceptance is separate: `RELEASE_BLOCKERS.md` assigns its
three crash windows to the PO. This finite scanner exception neither grants nor
replaces that acceptance, the final human-signature gate, or an independent
Security Reviewer signature.

### Finite exception identity, conditions, and re-review

The exception identity is the documented test purposes and fixture semantics in
this matrix, the `api-key` scanner rule, and exactly the eleven findings at
`5e15d62`—not permanently fixed line numbers. It covers no future finding.
It remains valid only while all conditions below hold:

1. **C1:** Finding count remains exactly 11.
2. **C2:** Every finding remains an intentional-positive test fixture.
3. **C3:** No real credential is present.
4. **C4:** No production/runtime/provider-credential reachability exists.
5. **C5:** Fixture-bearing files remain excluded from wheel and sdist.
6. **C6:** Scanner rules and exit semantics are not weakened.
7. **C7:** No allowlist or suppression is introduced.
8. **C8:** Fixtures retain their documented security-test purpose.
9. **C9:** No additional canonical finding is automatically covered.
10. **C10:** Any meaningful finding or fixture-semantic change is re-reviewed.

Re-review is mandatory if the count, rule, fixture semantics, test-file
classification, runtime reachability, wheel/sdist inclusion, scanner
architecture, or distribution mode changes; and before any public release,
bundle, container, or installer is considered.

The PO/TL also records a non-blocking post-release engineering follow-up: design
a first-class canonical scanner scope/intentional-fixture disposition mechanism
that preserves fail-closed behavior. It must not weaken rules, hide new
findings, or turn arbitrary test paths into exemptions. It is not current
release-critical work unless an authoritative future release document says so.

Adversarial review found no real secret, production/provider flow, wheel/sdist
inclusion, policy approval fabrication, scanner weakening, allowlist, fixture
change, TASK-016/B9/B11/ADR change, push, tag, or public release. Technical
review: **P0 0; release-critical technical P1 0; P2 0.**

## Required disposition

**SECURITY TECHNICAL RELEASE BLOCKER: RESOLVED FOR CURRENT CONTROLLED RELEASE.**
The independent Security Reviewer signature remains **OPEN / not named or
fabricated**, and the final human-signature gate remains **BLOCKED** because
the final release checklist's GO signatures and other independent gates are not
complete. The next authorized project action is recorded in the current release
documents; this exception does not authorize it itself.
