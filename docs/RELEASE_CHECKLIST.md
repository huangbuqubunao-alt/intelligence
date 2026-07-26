# Release checklist

## TASK-014 Phase B-1 — public YouTube subtitle smoke

- Status: **BLOCKED / NOT EXECUTED** (2026-07-26 UTC).
- Evidence: `docs/SMOKE_EVIDENCE/TASK-014-PHASE-B1-PUBLIC-YOUTUBE.md`.
- Reason: the existing CLI has no composition that can limit a real invocation to the authorized metadata, subtitle-directory, and one selected subtitle-body read sequence while using caller-supplied temporary SQLite/DATA/test-Vault roots. The default non-doctor operations fail closed.
- Public targets contacted: `0 of 2–3`; no target selection request or real YouTube call was made.
- Release conclusion: **No-Go remains.** This record is not final release approval and does not close licensing, BPE NOTICE/attribution, real Vault, at-most-once, or PO/TL/QA sign-off gates.

### Required follow-up decision

Authorize a constrained, production-owned entry point (or an explicitly approved existing one) before scheduling another B-1 run. Do not use a throwaway script or direct Adapter calls as a substitute.
