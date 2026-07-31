# Release Candidate Checklist

- Candidate version: `0.1.0`
- Candidate commit: (fill after merge)
- Status: `RC READY — code and automation complete`
- Last automated validation: 2026-07-31

## Automated Gate Results

| Gate | Command | Result |
|---|---|---|
| Lock consistency | `uv lock --check` | PASS |
| Offline sync | `uv sync --locked --offline` | PASS (61 packages) |
| Unit + integration tests | `pytest -x -q` | PASS (520 tests) |
| Type checking | `mypy src` | PASS (24 files) |
| Lint | `ruff check .` | PASS |
| CLI help | `youtube-intel --help` | PASS |
| Offline build | `uv build --offline` | PASS (sdist + wheel) |
| Git diff check | `git diff --check` | PASS |
| Security scan | `bash scripts/security_scan.sh` | PASS (13 checks) |
| Backup/recovery drill | `bash scripts/backup_recovery_drill.sh` | PASS (10 checks) |

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
- [x] Credential redaction in logs and error messages

## Feature Completeness

- [x] TASK-000: Product decisions closed
- [x] TASK-001: Project scaffold and quality gates
- [x] TASK-002: Configuration and domain contracts
- [x] TASK-003: SQLite state store
- [x] TASK-004: Channel discovery and metadata
- [x] TASK-005: Subtitle pipeline
- [x] TASK-005A: Local model shared contracts
- [x] TASK-006: Local Whisper transcription
- [x] TASK-007: Local Ollama scoring
- [x] TASK-008A: Cloud analysis shared contracts
- [x] TASK-009A: Obsidian shared contracts
- [x] TASK-008: Optional cloud deep analysis
- [x] TASK-009: Obsidian video notes
- [x] TASK-010: Pipeline orchestration and recovery
- [x] TASK-011: Weekly reports
- [x] TASK-012: CLI, scheduling, and logging
- [x] TASK-013A: Local transcription continuation
- [x] TASK-013: End-to-end acceptance
- [x] TASK-014: Release readiness (Phase A + B0-B11)

## Installation Verification

- [x] `pyproject.toml` declares Python >=3.12
- [x] `uv.lock` is consistent with `pyproject.toml`
- [x] CLI entry `youtube-intel` is registered
- [x] sdist and wheel build successfully
- [x] Config examples exist (`config/settings.example.yaml`, `config/channels.example.yaml`)
- [x] `.gitignore` prevents commit of `.env`, `/data/`, `/logs/`, `*.key`, `*.pem`

## Installation Steps (for operator)

```bash
# 1. Clone or extract the release candidate
# 2. Copy configuration templates
cp config/settings.example.yaml config/settings.yaml
cp config/channels.example.yaml config/channels.yaml

# 3. Edit configuration (replace placeholders, set real paths)
# IMPORTANT: Never put real API keys in settings.yaml
# Use environment variables or .env for credentials

# 4. Install with locked dependencies
uv sync --locked

# 5. Verify installation
.venv/bin/youtube-intel --help

# 6. Initialize the state database
# (requires running the migration — see operations.md)

# 7. Run doctor to validate configuration
.venv/bin/youtube-intel doctor
```

## Rollback Steps

```bash
# 1. Stop any running processes
# 2. Back up current data/
cp -r data/ data-backup-$(date +%Y%m%d)/

# 3. Revert to previous version
# (pip install previous version or checkout previous commit)

# 4. Restore data if schema is compatible
# (schema_migrations table must match)
```

## Uninstall Steps

```bash
# 1. Stop any running processes
# 2. Remove the virtual environment
rm -rf .venv/

# 3. Remove data and logs (CAUTION: this deletes all state)
# rm -rf data/ logs/

# 4. Remove the project directory
# cd .. && rm -rf youtube-intel/
```

## Post-Launch Verification

After deploying to a real environment:

1. `youtube-intel doctor` returns exit code 0
2. `youtube-intel check` discovers at least one channel
3. `youtube-intel process --video <id>` completes for one video
4. JSONL logs appear in `logs/operations.jsonl`
5. SQLite state reflects the processed video
6. (If enabled) Obsidian notes appear in the configured Vault

## Remaining Human-Decision Blockers

All items below are documented in `docs/RELEASE_BLOCKERS.md` and
require explicit human authorization before production deployment:

1. mutagen GPL distribution decision
2. o200k_base.tiktoken file-level license
3. OpenAI SDK / tiktoken / Jinja2 NOTICE evidence
4. MLX Whisper / ffmpeg / Ollama licensing
5. Cloud SDK isolation security review
6. Vault and template distribution boundary
7. At-most-once risk acceptance
8. Real backup/recovery drill
9. Four-phase real smoke authorization
10. Real Vault and launchd authorization
11. PO / TL / QA / Privacy Reviewer final signatures
