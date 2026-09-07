# TASK-022 Handoff — Personalized Distillation

## Metadata

- Task: `TASK-022 — Personalized Distillation`
- Role: `Implementer / adversarial reviewer`
- Approved predecessor: `659602c8791a4ede40c69d16012cf8701c34f6eb`
- Feature commit: `bae1c4477c2c0d1e0df88d313c241df3f62679e1`
- Worktree: `/Users/hua/Documents/yia-worktrees/task-022-personalized-distillation`
- Branch: `codex/task-022-personalized-distillation`
- Date: `2026-09-07`

## Scope and durable contract

Migration `010_add_personalized_distillation.sql` advances `v009 → v010`.
It adds only the TASK-022 execution checkpoint, immutable resource-usage
ledger, and immutable Intelligence card tables. Existing Source, Automation,
Evidence, Intelligence, Preference, policy, scoring, provider-dispatch, and
credential records remain authoritative. The runtime doctor now accepts the
current exact schema version `10`; migration regression fixtures retain their
historic slices explicitly rather than assuming m009 is always final.

`PersonalizedDistillationService` accepts only an injected offline,
deterministic test transport. There is no production provider adapter, API key,
network call, qualification claim, fallback, repair call, semantic retry, or
automatic retry. Budget is consulted before a transport invocation. A blocked
budget or unavailable transport persists truthful `WAITING_*` state with zero
calls and unknown usage. A transport exception becomes terminal `AMBIGUOUS`;
the same execution identity cannot redispatch.

The service projects only active TASK-020 preferences (including finite
horizon/provenance and statement) plus effective TASK-021 focus, ignore, and
style. Temporary focus at or past expiry is excluded. These inputs are immutable
command projection data; they cannot mutate Source policy, preferences,
schedules, limits, model choice, budget, or feedback. A normal skipped video is
ineligible. TASK-021 Manual Analyze can alter only relevance; budget, evidence,
transport, trust, and at-most-once gates remain in force.

Candidate JSON is parsed exactly once with an exact schema. Fences, malformed
objects, extra fields, `UNCLASSIFIED`, missing/foreign Evidence, generated text
as Evidence, incorrect ranges, and unsupported support sets fail closed before
admission. Every admitted revision has one finite classified claim kind and
legal canonical-transcript Evidence on the same linked Source/video. Evidence
support order is canonicalized before hashing, so reverse-order multi-Evidence
output remains readable. `FACT` is admitted as `NEW`, not `CONFIRMED`; `RUMOR`,
`OPINION`, `PREDICTION`, and `SYSTEM_INFERENCE` retain their explicit kinds.

Raw transport text is neither stored nor exposed as authority. Atomic admission
creates the revision, state history, Evidence links, `EVIDENCE_SUPPORT` edges,
card, checkpoint result, and immutable ledger. Only the existing
`AuthoritativeIntelligenceReader` mints `VerifiedIntelligenceRead`; its card
method revalidates the read, Source/video membership, Evidence target/ranges,
and content hash before the local API exposes card fields, source URL, and
Evidence time links. The API accepts no caller-selected provider, model, prompt,
or raw output.

No `m011`, Topic, cross-video dedupe, timeline, related topics, V2 flow, Deep
Analysis, real provider call, credential persistence, queue/orchestration, or
scoring-authority change is included.

## Verification

| Check | Result |
| --- | --- |
| TASK-022 migration/distillation/API/adversarial suite | `26 passed` |
| TASK-018/018A/019/020/021, scoring, dispatch/AMBIGUOUS, Source/Automation, local-API/runtime, state/migration, and Deep Analysis regression suite | `200 passed` |
| Full pytest | `2064 passed, 1 skipped, 1 existing Pydantic serializer warning` |
| `uv run --offline mypy src` | PASS, `49` source files |
| `uv run --offline ruff check .` | PASS |
| `uv build --offline` | PASS; existing build-system-version warning |
| `git diff --check` | PASS |
| `bash scripts/security_scan.sh` | Exit `1`, exactly `11` accepted existing synthetic fixture findings, `0` new TASK-022 findings; not scanner PASS |

## Adversarial review and re-review

Review covered caller-forged verified reads, raw/model-generated Evidence,
foreign Evidence, hallucinated ranges, FACT/lifecycle confusion, RUMOR and
SYSTEM_INFERENCE preservation, expired preference isolation, policy mutation,
skipped/manual eligibility, budget order, unavailable/mismatched transport,
actual-model identity, known/unknown usage and cost, credential columns,
malformed/fenced/partial output, no repair/retry/fallback, `AMBIGUOUS`, raw
output authority, Topic/m011 leakage, and real-provider absence.

Two concerns found during review were fixed before re-test:

1. Reverse-order multi-Evidence output previously produced a reader hash
   mismatch; admitted support is now canonicalized by Evidence ID.
2. Source membership used a display-list limit; an exact membership lookup now
   protects valid older linked videos and the reader path.

Re-review result: **P0 = 0, P1 = 0, P2 = 0** within TASK-022 scope.

## Frozen boundaries and handoff

TASK-016B/016C scoring and lineage semantics,
`AuthoritativeScoringReader`, `VerifiedScoringRead`, provider dispatch v4,
`AMBIGUOUS`, TASK-019 trust, TASK-020 preference separation, TASK-021 source
policy/filtering, credentials, qualification, Notes, Weekly V2, and TASK-016G
remain unchanged. Deep Analysis remains **BLOCKED / unchanged**. No remote
provider/model was called.

Recommended verdict: `APPROVE`.

`TASK-022 closed; ready for TASK-023 authorization.`
