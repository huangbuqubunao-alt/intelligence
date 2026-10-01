# V1X-DR-001: V1.x Content Deep Analysis

## Status

Accepted — records Owner-frozen V1.x product scope and the R3 architecture
consensus. Implementation proceeds on a separate V1.x branch; M13 dogfood stays
isolated.

## Date

2026-10-01

## Authority and scope of this record

This is a **new V1.x decision record**. It does **not** amend
`PRODUCT_CONSTITUTION.md`, `V1_PRODUCT_SPEC.md`, or
`V1_IMPLEMENTATION_ROADMAP.md`.

Deep Analysis, Obsidian Deep Analysis publishing, Home Knowledge Delta,
Research History, and Research Diff are **V1.x** capabilities. They were never
V1 commitments, and the historical V1 scope documents must not be rewritten to
imply otherwise. Product vocabulary authority remains
`PRODUCT_CONSTITUTION.md` > `V1_PRODUCT_SPEC.md` > `V1_IMPLEMENTATION_ROADMAP.md`
> Demo, unchanged by this record.

Deep Analysis extends the product; it does not rewrite V1 scope.

## Context

The M13 7-Day Dogfood closed a Summary/Evidence provenance P0 set whose design
lesson generalizes beyond Summary:

> MODEL-LOCAL OR TEMPORARY REFERENCES MUST NEVER BECOME DURABLE USER-FACING
> PROVENANCE. Backend Evidence authority owns durable Evidence identity. Any
> capability that cites Evidence must converge onto that same authority rather
> than introducing a parallel Evidence system.

Repository inspection during R3 confirmed that a large Deep Analysis
implementation already exists and is **dormant**: contracts, an admission
runtime, an append-only persistence store, cache/provenance machinery, and three
provider adapters. It is reachable only from the synthetic OpenAI qualification
harness. No HTTP route, no orchestration entry, and no user-facing surface exist.

R3 reviewed the proposed V1.x direction and returned product and technical
consensus, with the claim-structure fork resolved by Owner as option **B1-a**.

## Decision

### 1. Product position

Deep Analysis (深度分析) is a **Content-level advanced action**. Its
first-version product responsibility is *"Analyze one piece of Content deeply."*

It is **not** a primary navigation section, **not** a Summary replacement, and
**not** a new domain chain parallel to `Content → Intelligence → Topic`.

Initial scope is **Content only**. Deep Analysis of Intelligence or Topic is
deferred.

Deep Analysis answers a different question from Summary:

- Summary: "What does this content say?"
- Deep Analysis: "What are the important conclusions, what evidence supports
  them, what is uncertain, what it means for me, and what should I investigate
  next?"

### 2. Five-role first-version product contract

User-facing output focuses on exactly five concepts:

1. `CORE_CONCLUSION` / 核心结论
2. `KEY_EVIDENCE` / 关键证据
3. `UNCERTAINTY` / 不确定性
4. `RELEVANCE_TO_USER` / 对我的意义
5. `NEXT_QUESTION` / 下一步追问

Each projected claim carries text, epistemic type, confidence, and output
language. Stance is claim-relative. No single global result-level stance may
override claim-level semantics.

The five roles are a **user-facing projection** of the existing frozen
`KnowledgeContent` contract. They are not a second persistence schema, and they
do not weaken or fork the existing validated content contract.

### 3. RELATION_TO_KNOWLEDGE and KNOWLEDGE_DELTA are deferred

Neither role is model-answerable in the first version. R3 verified that
`CanonicalDeepAnalysisInputV1` carries no Intelligence, Topic, or prior-state
context, so asking the model for these roles would fabricate authority.

They belong to later Knowledge Delta / bounded knowledge-context work. They must
not be silently reintroduced.

Knowledge Delta is a **separate subsystem**, not part of Deep Analysis.

### 4. Backend durable Evidence becomes the citation authority (Phase 1B)

The dormant Deep Analysis `EvidenceRegistry` must **not** remain an independent
provenance authority. It is demoted: it may exist only as an internal transient
candidate set inside the admission boundary.

Before persistence or any user-visible projection, a transient ref must be
resolved through backend validation into durable Evidence identity
(`evidence.evidence_id`, minted deterministically by
`state.build_evidence_id`).

For the first version:

- **Citable:** trusted timed-transcript Evidence only.
- **Context only:** title, channel, description, other metadata. Context may
  inform reasoning but can never become citation authority.

No fabricated timestamps. No fabricated Evidence. No metadata promoted merely
because a model cited it.

### 5. Canonical-only / no-timed-Evidence Content fails closed

`evidence` requires a Content identity and a mandatory `start_ms`/`end_ms` span,
so a Content with a canonical transcript but no verified timed cues can never
mint durable Evidence. Deep Analysis for such Content must fail closed with an
honest unavailable state. It must never degrade to metadata-only citation and
must never invent a timestamp.

### 6. No generic router

No generic advanced model/task router is introduced. Narrow Deep Analysis
capability qualification is used, reusing the existing contract surface
(`DeepAnalysisProviderCapabilities.qualified_capability_profile_identity`,
`DeepAnalysisExecutionProfileV1.qualified_capability_profile_identity`).

### 7. Model qualification is an activation gate, not an architecture gate

Architecture consensus does not require a qualified model to exist.
Implementation may proceed; **user-visible production activation remains gated**
until at least one model/provider combination qualifies.

When nothing qualifies, the Deep Analysis path must truthfully show an
`UNAVAILABLE` / `NOT_QUALIFIED` state. It must never silently use a weaker
model, and must never fabricate a result.

`CONFIGURED ≠ AVAILABLE ≠ QUALIFIED ≠ PRODUCTION_ELIGIBLE`. Small local models
such as `qwen2.5-coder:7b` remain dev/test-only and are not assumed
production-qualified.

### 8. Cloud requires explicit per-run consent

If a cloud route is used: explicit user initiation, explicit per-run consent,
cost status disclosed **before** consent, no silent local→cloud fallback, no
surprise paid call, and no automatic retry that could duplicate a paid dispatch.
Bounded Evidence/context packaging is the default; an unrestricted full
transcript is not.

### 9. Cache identity

Results created under materially different Deep Analysis validation rules must
not alias each other. The existing distinct `validation_policy_identity` is the
capability identity for this purpose and is already part of cache identity
(A1 + A2 + A3 + validation policy). No existing unrelated scope field is
overloaded, and no new field is introduced for this.

### 10. Obsidian merge-key correction

Obsidian remains a one-way, user-owned projection; SQLite remains authority.

The Deep Analysis Obsidian **merge key is not `result_identity`**.
`result_identity` equals `provenance_identity` and incorporates the provider
envelope and payload identity, so it changes on every execution and cannot merge.

The merge key is a deterministic derivation of:

```text
content_identity + output_language + knowledge_content_schema_identity
```

`result_identity` and `cache_identity` are retained inside the note as
provenance fields. The Deep Analysis note uses its own note builder, validator,
and merge key, and is not forced through the existing video-note path. Obsidian
Deep Analysis publishing is deferred to Phase 2.

### 11. Branch and migration isolation

M13 dogfood continues independently. V1.x development uses a **clean separate
worktree and branch**, never branched from the dirty M13 working tree. No V1.x
feature is backmerged into M13 during the 7-day dogfood. M13 fixes may later be
forward-merged or cherry-picked into V1.x through normal reviewed Git history.

**Migration ordinal hazard.** M13 holds an in-flight migration `029` in its dirty
remediation. The clean reviewed anchor carries migrations only through `028`.
V1.x must not independently allocate a conflicting `029`; it reserves `>= 030` or
re-reads the actual next ordinal after M13 integration.

**Backup/Restore verification gap (identified by R3).** `_REQUIRED_TABLES` in
`backup_restore.py` is a 23-entry subset of 63 durable tables, checked with
subset semantics, and has no coverage test. `deep_analysis_persisted_results` is
already outside it. Phase 1B must add the new table and the existing Deep
Analysis table to backup verification, and add a coverage assertion. Until then,
"no durable table silently outside backup authority" is **not** enforced and must
not be claimed as satisfied.

## Consequences

- Phase 1A activates the existing dormant path without a schema migration. The
  five-role contract is delivered as a backend projection, and user-facing
  citations stay unavailable until Phase 1B durable-Evidence convergence.
- No new migration is allocated in Phase 1A. The ordinal stays at `028`.
- No qualified production model is implied. The honest unavailable state is the
  expected default until one qualifies.
- Knowledge Delta, Research, and Obsidian Deep Analysis remain unimplemented by
  design.

## Deferred

Generic router; Deep Analysis of Intelligence/Topic; persisted Knowledge Delta;
read watermarks; durable Research diff; Obsidian→SQLite round-trip; per-Following
output-language override; non-YouTube Evidence types (structurally impossible
under the current `evidence` schema and requiring a Constitution-level decision).
