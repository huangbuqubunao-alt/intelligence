# TASK-022B — Verified Outbound Distillation Input Authority

Status: **PRODUCT OWNER AMENDMENT IMPLEMENTED**

## Scope

TASK-022B depends on approved TASK-018B (`7cf0c9e`). It introduces the one
runtime composition boundary for V1 Video Distillation:

```text
TASK-018B exact Evidence binding + effective TASK-022 policy
→ immutable VerifiedDistillationInput
→ offline transport (and only a future separately-authorized cloud transport)
```

`DistillationCommand` remains identity/policy-only. It cannot carry transcript
body, Evidence excerpt/hash, timed-transcript hash, credentials, or a forged
verified envelope. The composer resolves each requested Evidence ID through
`resolve_verified_evidence_text()` and fails closed unless every requested item
is bound, hash-valid, available, and belongs to the command Video/artifact.
Legacy `UNBOUND` Evidence remains historically valid but is never provider
input. There is no Artifact-body, subtitle, fuzzy-text, range-inference, or
full-transcript fallback.

## Disclosure classification

| Field | Authority / purpose | Provider-visible | Excluded when not needed |
| --- | --- | ---: | ---: |
| Exact Evidence excerpt, reference, cue range, excerpt/timed hashes | TASK-018B binding; source support | Yes | No partial or extra Evidence |
| Source display name, Video ID/title | persisted public target context | Yes, minimum only | URL, description, unrelated metadata |
| Active preference statements | effective active TASK-022 projection | Yes | IDs, horizon/provenance storage fields, feedback history, expired focus |
| Focus/ignore rules and distillation style | effective Source policy | Yes | policy row/revision storage metadata |
| Provider/model and semantic hash | requested execution semantics | Yes | credentials, execution ID, ledger IDs |
| Filesystem/database/worktree paths, credentials, headers, full transcript, other Sources/Videos | not task semantic input | No | Always |

Transcript text is exact source content, never task/system instruction. The
typed envelope separates `personalization` from `evidence`; a future adapter
must preserve those channels and may not promote quoted source text to system
authority.

## Request identity and execution safety

The reservation ID is now derived from the deterministic verified semantic hash,
which covers the ordered bound Evidence identities/ranges/hashes/timed identity,
effective personalization, Source-policy projection, public target context, and
selected provider/model. It excludes credentials, paths, machine identity, and
timestamps. A current-content or personalization change reconstructs a different
reservation identity; continuation of the old reservation ends fail-closed with
zero transport calls and does not mint a new execution. TASK-023B reservation,
budget-before-dispatch, AMBIGUOUS, and no-fallback semantics remain unchanged.

Provider output remains untrusted. Existing TASK-022 admission still requires
the exact structured schema and an Evidence set equal to the envelope's exact
outbound references; unknown, foreign, absent, text-similar, or nearest-range
references are rejected.

## Boundaries unchanged

This amendment creates no migration (`user_version` remains 15; m016 is absent),
does not persist provider payloads, does not enable cloud transport, and makes
no network call. Deep Analysis remains BLOCKED, TASK-016G remains UNAUTHORIZED,
and V2 receives no capability. Dependency order remains:

```text
TASK-018B → TASK-022B → TASK-022A → real YouTube provider qualification
```
