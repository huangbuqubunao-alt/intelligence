# READINESS-PAGE-RECOVERY

Root assignment 2026-10-13; implementer `/root/caption_resume`.
Tree `/Users/hua/Documents/yia-worktrees/readiness-page-recovery`, branch
`codex/task-readiness-page-recovery`, base `1a401d7f688162adf5da01e6a30ab69d3e82ce52`.
Not a DONE/adoption record.

Real isolated API restart returned an empty HTTP500 Content response, then the
service recovered. The ordinary UI exposed JSON parse internals and had no local
read recovery action. Goal: understandable localized read failure and an explicit
bounded read-only reload without whole-app remount, mutation replay, hidden model
work, infinite retry or errors persisting across routes.

Allowed: frontend/src/workspace/App.tsx, uiLanguage.tsx, relevant App/client tests,
task and handoff. Root additionally approved existing
frontend/src/api/client.ts GET/HEAD failure mapping only; preserve machine-coded
4xx, qualification gates and all mutation behavior. No backend, Schema, security,
dependencies, production config/data, Cloud, GPU or source timing/Evidence changes.

Reuse DIRECT: React state/effects, existing useRemote/api/ErrorState and router,
existing UI tokens. No new dependency or external code. No new DESIGN.md needed
for this scoped state/copy repair; preserve the current design reference.

Checks: failing reproduction first, bounded retry/no write replay, route cleanup,
input preservation, full frontend, TypeScript, production build, diff check,
scoped commit/handoff and independent reviewer before integration.

Parallel: source_context owns distillation/tests in a different tree. Root handles
real API/browser acceptance after review; this task has no model/network authority.
