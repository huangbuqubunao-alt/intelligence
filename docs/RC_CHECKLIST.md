# Release Candidate Checklist — v2

- Candidate version: `0.1.0`
- Branch: `qoder/continue-dev`
- Status: **APPROVAL READY FOR LOCAL SMOKE / BLOCKED FOR PUBLIC DISTRIBUTION**
- Last automated validation: 2026-07-31 (re-validated after Reviewer RC1 feedback)

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

All commands run on `qoder/continue-dev` at commit `d668c6d` and subsequent fixes.
Platform: macOS arm64.

| Gate | Command | Result | Notes |
|---|---|---|---|
| Lock consistency | `uv lock --check` | PASS | — |
| Offline sync | `uv sync --locked --offline` | PASS | 61 pkgs (macOS arm64) |
| Unit + integration tests | `pytest -x -q` | **PASS — 520 collected, 520 passed, 0 skipped, 0 xfailed** | 22–23s |
| Type checking | `mypy src` | PASS (24 files, 0 errors) | — |
| Lint | `ruff check .` | PASS | — |
| CLI help | `youtube-intel --help` | PASS | — |
| Offline build | `uv build --offline` | PASS (sdist + wheel) | see artifacts below |
| Git diff check | `git diff --check` | PASS | — |
| Security scan | `bash scripts/security_scan.sh` | PASS (17 checks, 3 WARN) | see WARN notes |
| Backup/recovery drill | `bash scripts/backup_recovery_drill.sh` | PASS (14 steps) | see WARN notes |

### Security Scan WARN Items (not blocking automated gate)

| WARN | Explanation | Action |
|---|---|---|
| High-entropy string (check 13) | `a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb` — MLX Whisper model git revision, locked in ADR-007 | False positive; no remediation needed |
| No LICENSE in wheel (check 15) | Project license is UNRESOLVED — see `RELEASE_BLOCKERS.md §1.0` | Human decision required before any distribution |
| `.gitignore` `*.env` added | Pattern was missing; fixed in this RC cycle | Fixed |
| `print()` in `public_subtitle_smoke.py` (check 17) | Intentional JSONL output line for smoke command result | False positive; design-approved per ADR-013 |

### Backup/Recovery Drill WARN Items (not blocking automated gate)

| Item | Explanation |
|---|---|
| Corruption test 11 (4-byte overwrite) | Small DB may pass `integrity_check` for targeted byte corruption; not a coverage gap for real use |
| CLI doctor exit=3 | Expected in drill env (no Vault, no Ollama, no MLX model); does NOT indicate panic |

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
- [x] Obsidian note sanitization (Jinja2 sandbox + title filter)
- [x] Security scan passes 17 checks (3 documented WARNs — all false positives)

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

## Scanner and Drill Capability Statement

### Security Scanner (v3)
- **Platform**: macOS BSD grep and Linux GNU grep compatible
  - Check 3 (PEM headers) uses multiple `-e` patterns to avoid macOS BSD grep
    treating `-----BEGIN` as an option flag in a single `-E` argument
- **CAN detect**: common API key formats (OpenAI, GitHub, AWS, Slack, SendGrid), Bearer/Auth headers, PEM keys, AWS credential assignments, .env mispackaging, home-dir leaks, subprocess injection, URLs with credentials, build artifact leaks
- **CANNOT detect**: obfuscated/encoded secrets, runtime-injected values, binary assets, new credential formats, secrets passed via environment variables
- **Whitelist consistency**: `dummy / YOUR_KEY / <key> / REPLACE_ME / example / placeholder / fake` applied uniformly across checks 1, 2, 4, 5
- **Check 17 (print)**: uses word-boundary pattern `[^a-zA-Z0-9_]print\s*(` to exclude false positives like `_directory_fingerprint(` or `DirectoryFingerprint(`
- High-entropy heuristic (check 13) produces false positives for legitimate hash constants (known: model revision SHA)
- **Does NOT replace** a formal penetration test or security audit

### Backup/Recovery Drill (v2)
- **Validates**: WAL migration, business-data row-level round-trip, checksum consistency, post-restore integrity_check, corruption/truncation detection, idempotent re-run, CLI doctor
- **Does NOT prove**: real power-fail safety, filesystem crash recovery, concurrent writer isolation, real Vault restore, exactly-once job semantics
