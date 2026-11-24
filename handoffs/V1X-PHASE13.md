# Phase 13 — automatic Following continuous-goal handoff

Sole executor, no subagents. Authoritative starting main/origin HEAD:
`404d0a76ef022647f242e295a87b7ed18c3b0667`.
Candidate: `/Users/developer/Documents/yia-worktrees/phase13-background-following`,
`codex/phase13-background-following`. Main remains untouched unless **every**
acceptance criterion passes and topology is still clean/fast-forward safe.

Read the [decision](../docs/decisions/V1X-PHASE13-BACKGROUND-FOLLOWING.md),
[validation report](../docs/validation/phase13/REPORT.md),
[coverage](../docs/validation/phase13/COVERAGE.md) and
[self-review](../docs/validation/phase13/REVIEW.md).

Existing schema-34 next_check_at/source_checks/source_runs/observation ledger
remain authoritative. One serve-api worker executes checks serially and sleeps
on Event/deadline. Normal interval is 15 minutes; network/rate/provider/parser/
local failures have bounded durable retry. NOT_FOUND may be transient and retries
with provider-error backoff; state/risk/access refusal stops automatic calls at
all entry points. Manual network retry keeps five-second eligibility. No models,
notifications, settings, daemon, provider, migration or dependency were added.
Backup protects actual work, not idle scanning; Restore rebuilds the runtime
before scheduling resumes. SIGTERM/SIGINT drain the owning worker.

The live acceptance blocker is external to the candidate: real NASA and Google
Developers resolve canonical UC identities, but feed acquisition returns
NOT_FOUND on the current normal Mac SYSTEM_NETWORK route. A bounded comparison
on unchanged candidate and accepted-main provider code returns the same result.
The owner confirmed the VPN/proxy is active and forbade settings changes. A
normal automatic NASA attempt proves due admission, truthful failure, no Content
or models, and a one-hour future retry, but does **not** prove successful real
baseline/frontier. Do not waive that requirement or redesign Phase 12 networking.
Task-only offline injection is clearly separate from real public acquisition.

Task-owned runtime/evidence lives under `/tmp/intelligence-phase13-evidence`;
no user/production source authority or credentials were edited. The committed
validation evidence excludes SQLite databases/archives/credentials. All eight
protected worktrees, including dirty M13, match full before/after fingerprints.
Do not touch them.

The only permitted continuation is the same Phase 13 goal: close the real-source
acceptance gate on the unchanged normal route, rerun affected checks if needed,
refresh clean main/origin topology, require main ancestor of candidate, ff-only
adopt, push only origin main, fetch/verify equality, then mark Phase 13 complete
and feature development frozen for real-user daily usage/pilot. No Phase 14 or
new feature development is authorized. Never adopt while live acceptance fails.
