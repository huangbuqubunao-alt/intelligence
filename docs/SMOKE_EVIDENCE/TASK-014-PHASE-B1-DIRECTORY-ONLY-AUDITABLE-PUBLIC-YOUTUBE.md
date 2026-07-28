# TASK-014 Phase B-1 — Directory-only auditable public subtitle smoke evidence

- Status: `EXECUTED — evidence captured; TASK-014 remains IN_PROGRESS / No-Go`
- Execution baseline: `58f0215aa329b99d74429e8616bb5f8f673ef102`
- Control-plane authorization: `7983bf5bfa0ce08529d189a9ac07f41f042bc6a1`
- Scope: one authorized directory-only invocation after the required offline preprovision and static launcher verification.

## Preconditions

- The fixed offline preprovision sequence completed in the required order; each step exited `0`.
- The fixed absolute launcher existed, was executable, and statically mapped to `youtube_intel.cli:main`.
- A new temporary parent was created without recording its path; its `smoke-root` child did not exist before invocation.

## Safe stdout evidence

- Fixed invocation exit code: `0`.

| Public stable target identifier | metadata | enumerate | read | final safe code | directory diagnostic |
|---|---:|---:|---:|---|---|
| `--khbXchTeE` | 1 | 1 | 0 | `INVALID_RESPONSE` | `directory_unknown_invalid_response` |
| `JTxsNm9IdYU` | 1 | 1 | 0 | `INVALID_RESPONSE` | `directory_unknown_invalid_response` |

The table above is the complete safe stdout summary. No raw stdout, stderr, JSONL, temporary path, command text, URL, subtitle content, title, language, field value, exception, credential, payload, Cookie, user data, or media data is retained here.

## Stop point and limits

- The authorized invocation completed once; no retry or additional product command was run.
- Each fixed target has exactly one recorded summary with `metadata=1`, `enumerate=1`, and `read=0`.
- No authentication, Cookie, login, Vault, user data, media, ffmpeg, model, Ollama, OpenAI, paid service, launchd, push, merge, or source cleanup action was performed.
- This is bounded diagnostic evidence only. It is not a service-compatibility finding, risk acceptance, release approval, or final Go decision.
