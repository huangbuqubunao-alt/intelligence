# ADR-008 Cloud-SDK Isolation Security Review

## Scope and disposition

- **Review baseline:** `main@d493691` (2026-08-31).
- **Scope:** current project-owned OpenAI/Moonshot-compatible SDK integration,
  credential and subprocess boundaries, local/offline startup, ADR-008 local
  tokenizer ordering, and ADR-027 dispatch/consent controls.
- **Excluded:** live providers, real credentials, provider qualification,
  scanner redesign, BPE redesign, and release execution.
- **Security technical review:** **APPROVE** for the current controlled release
  posture. No P0 or release-critical technical P1 isolation defect was found.
- **Independent human Security Reviewer signature:** **OPEN**. This technical
  evidence records no named reviewer, human signature, legal approval, or final
  release approval.

## Normative contract recovered

ADR-008 A-03/A-08 require local admission, cache and budget gates before
credential resolution; A-09/A-14 prohibit SDK retries and hidden repair calls;
and A-17 requires no main-process SDK import, a literal child environment, no
inherited credential/proxy environment, SDK import before receipt of the
credential, and pipe-only credential transfer. ADR-028 requires the externally
provisioned `o200k_base.tiktoken` asset to fail closed with no network fallback.
ADR-027 requires explicit provider/consent binding, no `auto` mode or implicit
cloud escalation, a finite validated fallback DAG, non-secret DACS-1 identity,
and application-only `TrustedDeepAnalysisSuccess` minting.

These are normative controls. Use of an injected fake transport and a short-lived
child process is an implementation convention used to prove the controls
offline; installed `openai==2.46.0` is not itself client construction or network
activity.

## Static integration inventory

| Integration | Main-process SDK import/client | Credential and client boundary | Network/retry boundary |
| --- | --- | --- | --- |
| `providers/cloud_llm.py` legacy Responses provider | No `openai` import or client in the main process | `subprocess.Popen` with only `PYTHONNOUSERSITE`, `PYTHONDONTWRITEBYTECODE`, and `PYTHONUTF8`; child emits a ready handshake after SDK import, then receives the temporary credential on stdin | One child request; `store=False`, no tools/streaming, `max_retries=0`, 120 s bound |
| `openai_deep_analysis.py` reference adapter | No main-process SDK import or client | `python -I -c` with the same literal environment; child imports SDK before `sys.stdin.read()` receives the JSON pipe payload | One Responses request, 30 s, `max_retries=0`; no custom base URL |
| `kimi_deep_analysis.py` Moonshot-compatible adapter | No main-process SDK import or client | Same isolated `python -I` child and pipe-only payload; child imports SDK before stdin read | One Chat Completions request, fixed Kimi endpoint, 30 s, `max_retries=0` |

`runtime.py` may import the project-owned legacy provider class to assemble the
application, but that module contains the SDK only in its child-program string;
constructing the class does not start a child, resolve a credential, or call a
transport. Other standard-library HTTP users serve separately authorized
subtitle/discovery/local-loopback workflows and are not cloud-SDK activation.

## Isolation matrix

| Path | SDK import / client / credential / network | Explicit authorization and result | Evidence |
| --- | --- | --- | --- |
| Package import | `0 / 0 / 0 / 0` | No provider selected | socket-deny startup sentinel; no `openai` in `sys.modules` |
| CLI `--help` | `0 / 0 / 0 / 0` | No provider selected | socket-deny startup sentinel |
| Cloud disabled / low-value / cache / exhausted budget | `0 / 0 / 0 / 0` | Fails/skips locally; never selects cloud | `test_analysis_policy.py`, `test_summary_provider.py` |
| Cloud selected but credential missing | `0 / 0 / 1 resolver / 0` | Explicit enabled policy only; returns `CREDENTIAL_UNAVAILABLE` | focused service tests |
| OpenAI/Kimi prepared dispatch with fake transport | main `0 / 0`; fake transport exactly one only after explicit prepared dispatch and supplied synthetic credential | `CLOUD_EXPLICIT` consent, named provider, provider/profile/payload checks required | adapter tests |
| Local-only consent or invalid/`auto` consent | `0 / 0 / 0 / 0` | Contract rejects contradictory or `auto` state fail-closed | `test_deep_analysis_contracts.py` |
| Missing/wrong/malformed/symlinked BPE | `0 / 0 / 0 / 0` | Local `CONFIG_INVALID` path; no tokenizer download or provider path | `test_o200k_provisioning.py` |

The BPE gate applies to the ADR-008 legacy cloud-analysis path: `_input_tokens`
calls `load_provisioned_o200k_encoding` before cache/budget/credential handling.
The current ADR-027 OpenAI/Kimi reference adapters use their separately bound
conservative provider-context authority; they do not claim to use the local BPE
gate. Neither model silently changes provider.

## Credential, identity, and fallback review

- `EnvironmentCredentialResolver` is invoked only after enabled, local input,
  cache, and budget gates. Tests prove disabled/input-too-large/budget/cache
  branches make zero resolver and transport calls.
- The child environment excludes `OPENAI_*`, `AZURE_*`, proxy variables,
  `PYTHONPATH`, and `*_TOKEN`/`*_KEY`/`*_SECRET`/`*_PASSWORD` values. The child
  imports the SDK before pipe receipt; credentials are not passed by argv,
  environment, or file.
- Request projections, credential execution-profile identities, cache identity,
  persistence/provenance models, adapter errors, and exposed responses exclude
  credential material. Synthetic-sentinel tests assert that absence.
- There is no automatic provider selection, credential-presence selection,
  local-to-cloud escalation, or OpenAI-to-Kimi/Kimi-to-OpenAI failure fallback.
  ADR-027 permits only an explicit, finite, acyclic, consent-bound fallback DAG;
  invalid, cyclic, ambiguous, re-entry, or `auto` configurations fail closed.
- Provider output is untrusted until the application validation finalizer mints
  `TrustedDeepAnalysisSuccess`; adapters export no mint authority.

## Offline evidence

| Check | Result |
| --- | --- |
| Focused admission, credential, BPE, provider-adapter, persistence tests | `235 passed, 1 skipped` |
| Socket-deny package import and CLI-help sentinel with synthetic cloud environment values | SDK clients `0`; network attempts `0`; `openai` absent from main-process module set |
| Existing child import-environment sentinel | confirms `openai==2.46.0` import with an empty blocked-variable set and no parent sentinel leakage |
| Existing fake transport/construction sentinels | selected fake provider only; missing credential fails before transport; disabled/cache/budget paths are zero transport calls |

No live provider, DNS query, HTTP request, real credential, provider
qualification action, scanner change, BPE redesign, push, tag, or release was
performed by this review.

## Adversarial review and re-review triggers

The review challenged eager imports, CLI initialization, credential-before-gate
ordering, unexpected socket use, SDK retry, implicit/cross-provider fallback,
credential persistence, trusted-output minting, and BPE-after-cloud ordering.
All were rejected by the current static trace and offline tests. **P0: 0;
release-critical technical P1: 0; P2: 0.**

Re-review is required if any cloud adapter, subprocess invocation, child
environment, credential resolver, provider-selection/fallback policy, SDK
version/transport policy, persistence surface, BPE admission ordering, or
distribution mode changes.
