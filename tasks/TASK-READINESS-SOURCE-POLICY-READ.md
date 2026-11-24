# TASK-READINESS-SOURCE-POLICY-READ

- Status: READY (ordinary-user readiness candidate only)
- Implementer: /root/source_context; Reviewer: /root/intel_bounded_review, after retirement review.
- Base: codex/task-end-to-end-user-readiness@d903c60
- Worktree: /Users/developer/Documents/yia-worktrees/readiness-source-policy-read
- Branch: codex/task-readiness-source-policy-read

## Goal and done criteria

ExistingSourceForm must not represent a failed GET of global policy as “未设置/Not set”. Show a localized, actionable read error and an explicit retry of that read, preserve form drafts, and prevent policy-dependent actions until the true read succeeds. Retry never submits or replays a mutation. Preserve all existing policy editing, authorisation and backend behaviour.

## Allowed scope

frontend/src/workspace/App.tsx, frontend/src/workspace/uiLanguage.tsx, their existing frontend tests (and focused new tests if necessary), this task copy, and handoffs/TASK-READINESS-SOURCE-POLICY-READ.md. No backend, Schema, dependencies, lockfiles, toolchain, config, credentials, model calls, formal data, or main changes.

## Reuse decision

DIRECT existing ApiClient and page read recovery/localized ErrorState components; ADAPT the existing form lifecycle with minimal local state. No new dependency or UI redesign. Consult existing DESIGN.md if present; no unrelated design churn.

## Required evidence

First reproduce failed/unparseable/empty policy GET and truthful success/absence distinction. Cover manual retry success, repeated failure, navigation/unmount, preserved drafts, policy-dependent disabled state, and zero POST/PATCH from retry. Do not weaken existing tests. Run frontend full tests, TypeScript, production build, git diff --check; review full diff and write exact handoff with SHA. Root conducts real headful acceptance after integration.

## Coordination

Parallel now: retirement Reviewer and root isolated GUI read acceptance, neither changes this frontend scope. Waiting: raw capture persistence (security-sensitive proposal and backend retirement integration), new model weights (specific user approval pending). Worker commits bounded implementation, then stops; no main merge or task DONE.
