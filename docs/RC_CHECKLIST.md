# Release Candidate Checklist — v2

- Candidate version: `0.1.0`
- Branch: `qoder/continue-dev` (remediation branch: `workbuddy/fix-rc-p1`)
- Base commit: `296f701` (`qoder/continue-dev` HEAD)
- Status: **P1 REMEDIATION COMPLETE — READY FOR CODEX REVIEW / BLOCKED FOR PUBLIC DISTRIBUTION**
- Last automated validation: 2026-08-11 (after P1 remediation)

---

## Dependency Package Counts (Accurate Statistics)

> **WARNING**: The previous version of this file stated "61 packages" without specifying
> the counting method. That figure was the current-platform installed count and was
> misleading. Accurate counts are:

| Statistic | Value | Command to reproduce |
|---|---|---|
| `uv.lock` total packages (cross-platform, all conditions) | **84** | `grep -c '^name = ' uv.lock` |
| Current platform installed (macOS arm64, runtime+dev) | **61** | `uv pip list \| tail -n +3 \| wc -l` |
| Direct runtime dependencies (`pyproject.toml`) | **7** | see `[project] dependencies` |
| Direct dev dependencies (`[dependency-groups].dev`) | **3** | see `[dependency-groups]` |

> Note: The 84-vs-61 gap is explained by cross-platform conditional packages
> (CUDA, NVIDIA, torch/triton Linux-only, etc.) that are resolved in the lock file
> but not installed on macOS arm64. Package counts WILL vary by platform, Python
> version, and which extras/groups are synced.

---

## Automated Gate Results

All commands run on `workbuddy/fix-rc-p1` after P1 remediation.
Platform: macOS arm64.

| Gate | Command | Result | Notes |
|---|---|---|---|
| Lock consistency | `uv lock --check` | PASS | — |
| Offline sync | `uv sync --locked --offline` | PASS | 61 pkgs (macOS arm64) |
| Unit + integration tests | `pytest -x -q` | **PASS — 583 collected, 583 passed, 0 skipped, 0 xfailed** | ~29s |
| Type checking | `mypy src` | PASS (24 files, 0 errors) | — |
| Lint | `ruff check .` | PASS | — |
| CLI help | `youtube-intel --help` | PASS | — |
| Offline build | `uv build --offline` | PASS (sdist + wheel) | see artifacts below |
| Git diff check | `git diff --check` | PASS | — |
| Security scan | `bash scripts/security_scan.sh` | PASS (status=clean, WARN items reviewed) | see WARN notes |
| Backup/recovery drill | `bash scripts/backup_recovery_drill.sh` | PASS WITH WARNINGS (17 pass, 1 warn, 0 fail) | see WARN notes |

### Security Scan WARN Items (not blocking automated gate)

| WARN | Explanation | Action |
|---|---|---|
| High-entropy strings | Legitimate hash constants / model revision SHAs / test fixtures; locked in ADR-007 and test code | False positives; no remediation needed |
| No LICENSE in wheel | Project license is UNRESOLVED — see `RELEASE_BLOCKERS.md §0.1` | Human decision required before any distribution |
| `print()` in `public_subtitle_smoke.py` | Intentional JSONL output line for smoke command result | False positive; design-approved per ADR-013 |

### Backup/Recovery Drill WARN Items (not blocking automated gate)

| Item | Explanation |
|---|---|
| CLI doctor exit=3 | Expected in drill env (no Vault, no Ollama, no MLX model); doctor runs without panic |

---

## Build Artifacts

| Artifact | Path | Approx. size |
|---|---|---|
| Source distribution | `dist/youtube_intel-0.1.0.tar.gz` | ~1.8 MB |
| Wheel | `dist/youtube_intel-0.1.0-py3-none-any.whl` | ~1.9 MB |
| LICENSE in wheel? | **ABSENT** | Blocked — see §1.0 below |

---

## Project License Status

- **No LICENSE file exists** in the repository root.
- `pyproject.toml` has **no `license` field**.
- `docs/SBOM.md` explicitly states: *"本任务不选择、创建或暗示项目自身 LICENSE"*.
- `docs/THIRD_PARTY_NOTICES.md` is `DRAFT — RELEASE BLOCKED`.
- **No evidence** in any document, commit message, or ADR establishes what license
  governs the project's own code.
- **Consequence**: Until a project license is chosen and a LICENSE file is added,
  the build artifact does not satisfy standard distribution requirements.
  Recipients have no explicit grant of rights.

---

## Code Quality

- [x] No TODO/FIXME/HACK in source
- [x] No `NotImplementedError` in source
- [x] No `pytest.mark.skip` or `xfail` in tests
- [x] No credential assignments in source
- [x] No hardcoded secrets in tests
- [x] No subprocess shell=True
- [x] No eval/exec usage
- [x] Path traversal protection in place
- [x] Cloud SDK isolation implemented (ADR-008)
- [x] Atomic file writes with fsync
- [x] Obsidian note sanitization (context-aware inline/block escaping + URL scheme validation + marker shape validation)
- [x] Security scan passes with documented WARNs (all false positives)
- [x] Backup/recovery drill deterministic corruption detection and idempotent re-verification

---

## Feature Completeness

- [x] TASK-000 through TASK-013 (all DONE per docs/PROJECT_STATUS.md)
- [x] TASK-014 Phase A + B0–B11 (directory contract diagnostics)

---

## Installation Verification

- [x] `pyproject.toml` declares Python >=3.12
- [x] `uv.lock` is consistent with `pyproject.toml`
- [x] CLI entry `youtube-intel` is registered
- [x] sdist and wheel build successfully (offline)
- [x] Config examples exist
- [x] `.gitignore` prevents commit of `.env`, `*.env`, `/data/`, `/logs/`, `*.key`, `*.pem`
- [ ] **LICENSE file: ABSENT** — human decision required

---

## Differentiated Release Conclusions

| Readiness Level | Status | Blocking Reasons |
|---|---|---|
| ① Code is testable (unit + integration) | **YES** | — |
| ② Personal local smoke (no distribution) | **YES** | Smoke authorization matrix gates remain (SMOKE_AUTHORIZATION_MATRIX.md) |
| ③ Merge to main | **CONDITIONAL** | Requires Integrator + Orchestrator approval per COLLABORATION.md |
| ④ Public distribution (pip install / upload to PyPI) | **NO** | License unresolved; mutagen GPL; o200k_base.tiktoken; SBOM gaps; NOTICE not complete |
| ⑤ Production deployment | **NO** | All ④ items plus: at-most-once risk acceptance, real backup drill, four-phase smoke, final signatures |

---

## Remaining Human-Decision Blockers

All items documented in `docs/RELEASE_BLOCKERS.md`.
Summary of **distribution-blocking** items:

1. **[DIST BLOCKER]** Project license: not selected, no LICENSE file, no `license` field in pyproject.toml
2. **[DIST BLOCKER]** mutagen GPL-2.0-or-later distribution form decision
3. **[DIST BLOCKER]** `o200k_base.tiktoken` file-level license and NOTICE
4. **[DIST BLOCKER]** OpenAI SDK / tiktoken / Jinja2 NOTICE evidence gap
5. **[DIST BLOCKER]** MLX Whisper / ffmpeg / Ollama licensing decision
6. Cloud SDK isolation security review sign-off
7. Vault and template distribution boundary sign-off
8. At-most-once risk acceptance (PO)
9. Four-phase real smoke authorization
10. Real Vault and launchd authorization
11. PO / TL / QA / Privacy Reviewer final signatures

---

## P1 Remediation Evidence

Three P1 blockers from Codex Maintainer Review were remediated on `workbuddy/fix-rc-p1`:

### P1-1 Security Scanner
- Rewrote `scripts/security_scan.sh` to invoke `scripts/_security_scan.py`.
- Credential patterns now use Python `re` with explicit spacing and quote handling; works on macOS BSD and Linux.
- Added AST-based detection for `subprocess.run/Popen/call/check_call/check_output(..., shell=True)`.
- Scanner is fail-closed: any read/extract/AST failure returns non-zero.
- Findings are redacted: output is `rule=... path=... line=... fingerprint=...` only.
- Expanded scan scope to all Git-tracked `.py/.sh/.toml/.yaml/.yml/.json/.md/.txt/.cfg/.ini` plus wheel and sdist contents.
- Added `tests/scripts/test_security_scan.py` with positive/negative probes.

### P1-2 Backup/Recovery Drill
- Rewrote `scripts/backup_recovery_drill.sh` (v3) with explicit PASS/WARN/FAIL state model.
- Corruption detection is deterministic: SQLite header corruption, 50% truncation, manifest checksum mismatch, recovered-file checksum mismatch.
- Data-level verification covers schema, user_version, migration record/checksum, videos, jobs, key business fields, row counts, integrity_check, backup/recovered checksums, read-only query, and CLI doctor.
- Idempotency is proven by re-verifying the SAME recovered database object and checking row counts do not change.
- Honest limitations statement preserved: real power-fail, kernel crash, concurrent writes, real Vault restore, and exactly-once are NOT proven.

### P1-3 Obsidian Markdown/HTML Safe Rendering
- `src/youtube_intel/notes.py` now distinguishes `_safe_inline()` (single-line primitives) and `_safe_block()` (multi-line body text), with context-appropriate escaping.
- HTML boundary characters are escaped; Markdown links/images/wiki-embeds/headings/blockquotes/lists/code/horizontal-rules are neutralized.
- Source URL scheme is validated; only `http`/`https` are allowed.
- Marker shape validation ensures auto/user region markers remain template-controlled.
- `src/youtube_intel/reporting.py` applies the same escaping to weekly-report items, keywords, and directions.
- Added `tests/unit/test_weekly_rendering.py` and expanded `tests/unit/test_note_rendering.py` to cover payloads and user-region preservation.

## Scanner and Drill Capability Statement

### Security Scanner (v4)
- **Platform**: Python 3 stdlib only inside the helper; shell wrapper is POSIX-compatible (macOS BSD and Linux GNU)
- **CAN detect**: common API key formats (OpenAI, GitHub, AWS, Slack, SendGrid), Bearer/Auth headers, PEM keys, AWS credential assignments, generic credential assignments with spacing/quote variants, .env files, URLs with credentials, subprocess `shell=True` via AST, high-entropy strings, print calls, build-artifact leaks
- **CANNOT detect**: obfuscated/encoded secrets, runtime-injected values, binary assets, new credential formats, secrets passed via environment variables
- **Whitelist consistency**: `dummy / YOUR_KEY / <key> / REPLACE_ME / example / placeholder / fake / test_fixture` applied uniformly
- **Fail-closed**: Git enumeration failure, file read failure, AST parse failure, wheel/sdist extract failure, and incomplete scan steps all return non-zero
- **Redaction**: findings never echo the matched secret; only rule, path, line, and short SHA-256 fingerprint are printed
- High-entropy heuristic produces false positives for legitimate hash constants (known: model revision SHA, test fixture hashes)
- **Does NOT replace** a formal penetration test or security audit

### Backup/Recovery Drill (v3)
- **Validates**: WAL migration, migration checksum round-trip, schema/user_version, representative business-data row-level round-trip (videos, jobs), deterministic corruption rejection (header, truncation, manifest checksum, file checksum), idempotent re-verification on the same recovered object, read-only post-recovery query, CLI doctor without panic
- **Does NOT prove**: real power-fail safety, filesystem crash recovery, concurrent writer isolation, real Vault restore, exactly-once job semantics
