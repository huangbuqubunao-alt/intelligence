# TASK-014 Phase B-1 — B6-classified directory-only public subtitle evidence

- Date: `2026-07-28`
- Execution source: `codex/task-014-phase-b1-directory-only-b6-execution@756e7e4f5313b7d077bdca8e1154a13cc4db2e57`
- Control-plane authorization: `5b7dcca2ba9bd9e52e254a8944e584542838e24b`
- Scope: one authorized B6-classified `directory-only` public-subtitle smoke.
- Release state: `TASK-014` remains `IN_PROGRESS / No-Go`.

## Preconditions

| Check | Result |
|---|---|
| Required branch, HEAD, authorization ancestry, and clean source | PASS |
| `uv lock --check` before provisioning | PASS |
| `uv sync --locked --offline` | PASS — completed without lockfile change or download indication |
| `uv lock --check` after provisioning | PASS |
| Absolute launcher exists, is executable, and statically maps to `youtube_intel.cli:main` | PASS |
| Fresh temporary parent and absent `smoke-root` confirmed before the call | PASS |

## One-time safe stdout summary

The authorized call was made once, after the preconditions above. Its numeric exit code was `0`.
Only the stable public target identifiers and fixed safe fields below are retained.

| Target | metadata | enumerate | read | Final safe code | ADR-017 directory diagnostic |
|---|---:|---:|---:|---|---|
| `--khbXchTeE` | 1 | 1 | 0 | `INVALID_RESPONSE` | `directory_shape_unknown` |
| `JTxsNm9IdYU` | 1 | 1 | 0 | `INVALID_RESPONSE` | `directory_shape_unknown` |

## Boundary and conclusion

- No second attempt, retry, alternate entry point, PATH change, authentication, Cookie, media, Vault, model, OpenAI, Ollama, or user-data access occurred.
- No raw stdout, stderr, JSONL, temporary path, command text, URL, subtitle content, title, language, field value, exception, payload, or credential material is retained here.
- This is completed B6-classified directory-only execution evidence, not a claim that either target's subtitle directory was accepted, a general real-service compatibility finding, a risk acceptance, or release approval. `TASK-014` remains `IN_PROGRESS / No-Go`.
