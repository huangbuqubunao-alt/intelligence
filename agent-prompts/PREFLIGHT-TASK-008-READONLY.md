# TASK-008 read-only preflight — cloud analysis contracts and privacy

Role: Read-only Scout. Work only in `/Users/developer/Documents/youtubek agent`.

This packet authorizes inspection only. Do not modify or create any repository or temporary
file, stage/commit, create a branch/worktree, run uv/tests/builds or Python imports, install
packages, access the network, inspect environment-variable values, access credentials,
call OpenAI or any other Provider, or change task status.

## Authorization and baseline

At start, resolve:

```bash
git log -1 --format=%H -- agent-prompts/PREFLIGHT-TASK-008-READONLY.md
```

It must equal current clean main HEAD. Confirm TASK-006 and TASK-007 are `DONE`, while
TASK-008 is `BLOCKED/UNASSIGNED`. If main changes or becomes dirty during the Scout, stop
and report it; do not clean or wait on a writer.

Read fully in repository order: `AGENTS.md`, `docs/COLLABORATION.md`,
`docs/PROJECT_STATUS.md`, `docs/PRD.md`, `docs/SYSTEM_DESIGN.md`,
`docs/REUSE_REGISTER.md`, `docs/PRODUCT_DECISIONS.md`,
`docs/decisions/ADR-002-config-domain-contracts.md`,
`docs/decisions/ADR-003-sqlite-state-store-contract.md`,
`docs/decisions/ADR-007-local-model-pipeline-contracts.md`,
`tasks/TASK-008-deep-analysis.md`, and this packet. Inspect current source/tests/config/
lockfile statically. The repository is not CodeGraph-indexed; do not create an index.

## Questions to close

Produce evidence, not an implementation:

1. **Public contracts** — inventory the exact current `AnalysisInput`, `AnalysisResult`,
   evidence/point types, `SummaryProvider`, cloud config, Artifact kinds, Provider-call
   records, Pipeline/Job states and `complete_stage` surface. Identify any missing field,
   forbidden free-form mapping, or shared-contract change. Do not invent a parallel type.
2. **Eligibility and zero-call matrix** — freeze the order and observable result for cloud
   disabled, low final score, missing key reference, budget exhausted, invalid privacy
   input, oversize input, cached success, cached failure/retry and allowed high-value
   input. Clarify who owns per-run budget reservation/refund and how concurrent attempts
   avoid exceeding five calls.
3. **Data minimization** — enumerate the exact metadata/transcript fields allowed to leave
   the machine; explicitly exclude Obsidian/user content, local paths, secrets and
   diagnostics. Define bounded input construction and whether transcript sampling reuses
   an existing sampler or needs a separately approved contract.
4. **Token and cost boundary** — determine how the existing `30,000 input token` limit can
   be measured deterministically for a configurable OpenAI model, including unknown-model
   behavior, system/prompt/schema overhead, preflight rejection and recorded usage. Flag
   any need for a direct tokenizer dependency rather than silently relying on a transitive
   package.
5. **Secret lifecycle** — trace `cloud.api_key_env` from validated name to runtime value
   without reading any value. Specify injection/test seams, absence behavior, repr/error/
   traceback/log redaction, and the boundary between config validation and Provider
   construction.
6. **Adapter and response safety** — compare official OpenAI SDK reuse against a standard
   library HTTP Adapter. Recommend `DIRECT/ADAPT/REFERENCE/REJECT`, but do not guess a
   version unavailable offline. Cover base URL ownership, timeouts, bounded reads,
   structured output, one repair attempt, HTTP/SDK error mapping, `Retry-After`, response
   closure and exception-graph redaction.
7. **Cache/transaction/recovery** — map request hash dimensions, raw and structured
   Artifact keys, Provider-call reservation/lease/completion, cache validation, file
   atomicity, `SCORED -> ANALYSIS_READY`, structured skip results, rollback points and
   requeue behavior onto existing Repository methods. Determine whether TASK-008 can be
   implemented without Schema/migration or `state.py` changes.
8. **Analysis semantics** — map every required PRD/System Design output, distinguish fact,
   inference and recommendation, bind evidence IDs and transcript timing, and define
   fail-closed validation for fabricated/missing citations and untrusted model content.
9. **Scope and tests** — propose the smallest vertical file/test split. Include Fake-only
   eligibility, budget, redaction, malformed/bounded response, cache, temporary
   SQLite/artifact rollback and zero-network tests. If the task exceeds a focused M slice
   or needs shared contracts, propose a prerequisite TASK-008A rather than expanding the
   Implementer silently.
10. **Approvals** — list separately what is already approved and what still requires
    product-level or task-level approval: exact direct dependencies/versions, lockfile and
    downloads, network research, credential presence, paid/real calls, input data,
    retention, budget, file scope and verification commands.

## Required response

Return only a concise structured report:

```text
Preflight: TASK-008
Role: Read-only Scout
Observed main commit:
Repository changes: None
Spec/contract consistency: PASS | DECISION NEEDED
Existing contract/repository inventory:
Eligibility/privacy/budget matrix:
Token-count recommendation:
Secret/Adapter/reuse recommendation:
Cache/transaction/recovery recommendation:
Suggested task split and exact file groups:
Offline test matrix:
Already approved:
Approvals still needed:
Risks/blockers:
Proposed decisions A-01...:
Recommended next action:
```

Do not claim a dependency version was verified unless present in the repository. Do not
write a handoff or commit. End by confirming `git status --short` has no changes.
