# TASK-READINESS-Q3KS-DIAGNOSTIC

Status: IN_PROGRESS, isolated QA only, 2026-10-24.

## Goal and done criteria

Test one fixed lower-memory, pure-text 9B quantization through the existing
Qwen3.5 adapter without redevelopment. Prepare a narrowly adapted diagnostic,
independently review its frozen inputs and offline tests, then root may execute
at most one original English generation. Preserve every original failed result.
No production qualification, receipts, other cases, paid cloud, or owner data.

## Assignment

- Implementer: `/root/model_diagnostic_qa_writer`.
- Worktree: `/Users/developer/Documents/yia-worktrees/readiness-model-diagnostic`.
- Base: existing clean QA branch, record its exact HEAD before modification.
- Reviewer: `/root/long_completion_review_r1`, after implementer clean STOP.
- Root: freeze exact request/manifest/package, resource and ownership checks,
  actual once-only execution and independent semantic review.
- Parallel now: independent configurable-model-binding review in its own WT.
- Waiting: no model execution before independent diagnostic approval; no
  integration/publication before the complete Goal gates.

## Authorization and reuse

User's continuing default approval explicitly permits necessary isolated local
model changes and resource management. Codex and Jimmm VPN must remain running.
DIRECT existing fixed Ollama 0.40.9 and Python standard library; ADAPT the already
reviewed original thinking diagnostic, not the failed nonthinking candidate.
Original script SHA256:
`5c8452261640c43c3b3c7ed02378c32a9160fadc620dd1113e45ce590af800d0`.
No dependency, schema, production configuration or business lifecycle changes.

## Artifact and request freeze

See `BOUNDED_9B_TEXT_Q3KS_PREFLIGHT_2026_10_24.json` and
`Q3KS_ISOLATED_ARTIFACT_VERIFICATION_2026_10_24.json` under this Goal's validation
directory. Third-party Unsloth standard Q3_K_S, Apache-2.0, fixed source revision
`3885219b6810b007914f3a7950a8d1b469d598a5`; not an official Ollama artifact.

Isolated directory:
`/Users/developer/Documents/yia-worktrees/end-to-end-user-readiness/.var/end-to-end-user-readiness/qwen35-9b-text-q3ks-20261024`.
Daemon `127.0.0.1:11438`, store `models`, no cloud, one loaded model/parallel slot.
Tag `intelligence-qwen35-9b-text-q3ks:3885219b`.
Manifest `4070000a6455cb321fd5f0f07974368573e66650db4ade1e920ee384f3f279f7`.
Canonical manifest is a normal blob file; v2 tag reference is a relative symlink.
Require the exact reference target and unchanged lstat/readlink at each boundary.
Exactly four fixed payloads, no projector or `--mmproj`; reject unknown payloads.
The external Applications installation changed to0.40.10 before execution.
Use the separately verified official0.40.9 archive in the fixed isolated
`pinned-ollama-0409-20261024/runtime` directory. All three critical hashes match
the original0.40.9 bytes; no Applications install or owner configuration change.
Bind the actual daemon PID/start/argv through the new frozen `daemon_owner`
package entry. The unchanged old package remains historical evidence.
The independent Mach-O and actual `vmmap` evidence establishes an ARM64-only
diagnostic contract. Do not require the x86-only implementation dylib on ARM64.
Prove actual process Code Type/PID/launch against the same process observation;
require the exact main executable mapping, reject unknown/Rosetta/x86 and
inappropriate implementation mappings. Preserve the rejected unconditional
guard and its review evidence; do not implement an x86 dependency framework.
Fresh resource lower bound is actual complete payload bytes plus 2 GiB,
6464360941 bytes. This is not a peak-memory guarantee or a relaxed old-model gate.

Only top-level model changes from the original real-deepthink-en request. Keep
all original messages, Evidence, format/schema, focus, thinking=true, sampling,
8192 output budget, 16384 context, 512 batch, seed and 300-second deadline.
Actual native full rendering/token count and idle slot context must prove
N+P+2<=C; no truncated prompt, repaired output, case substitution or retry.

## Allowed QA changes and required checks

Only new ignored `.var/model-diagnostic-q3ks` diagnostic/tests/evidence and this
task's handoff. Do not modify original QA scripts, failed outputs, production
source, qualifications or registry. Author makes no HTTP/load/generation calls.
Use a separate exclusive once marker and output scope. Retain original raw-byte
capture before parsing, timeout, resource, runtime, ownership and native checks.
Test reference swaps, foreign model, unknown payload, unexpected projector,
one-shot reuse, nonempty preload and absence of qualification authority.
Run the complete offline diagnostic test file, compile and Ruff, inspect diff,
record hashes and clean STOP. Independent review reruns checks before root runs.

## Outcome policy

The first actual result ends this diagnostic. Failure remains failed and stops
this candidate. Success alone grants no qualification: any later adoption needs
a separately recorded central descriptor, complete original YT/LOCAL/long
qualification from case one, and the real GUI/save/topic/evidence/restart/backup
restore checks. No changes to semantics or standards to manufacture success.
