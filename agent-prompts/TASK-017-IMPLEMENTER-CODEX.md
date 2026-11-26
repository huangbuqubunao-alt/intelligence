# TASK-017 — FCC-Inspired Product Workspace Presentation Refactor

## Assignment

```text
Task: TASK-017
Role: Codex Implementer
Base anchor: main@943e1a73b56aecba988d2bd847f9f3031b2f1752
Worktree: /Users/developer/Documents/yia-worktrees/task-017-fcc-inspired-ui
Branch: codex/task-017-fcc-inspired-ui
Allowed scope: tasks/TASK-017-fcc-inspired-workspace-presentation.md
Required checks: task card "Required validation"
Reuse decision: REFERENCE — Alishahryar1/free-claude-code current main, MIT
```

Before changing code, confirm this task's governance authorization is an
ancestor of the branch, the worktree is clean, and read `AGENTS.md`, the task
card, `docs/PRD.md`, `docs/FRONTEND_PRODUCT_ARCHITECTURE.md`,
`docs/LOCAL_PRODUCT_ORCHESTRATION.md`, `docs/REUSE_REGISTER.md`, and this
packet. Do not implement in `main`.

## Scope contract

Implement the presentation-only refactor authorized by TASK-017. Study only
the necessary current-`main` Free Claude Code presentation source; record its
commit, MIT license and an ADOPT/ADAPT/REJECT mapping in
`docs/FCC_UI_DESIGN_REFERENCE.md`. Reimplement design principles in the
existing React/CSS structure. Do not copy FCC source substantially, branding,
assets, unique copy, runtime/configuration behavior, dependencies or
screen-for-screen layouts.

Preserve the approved local workspace IA: Dashboard, Sources, Source Detail
Drawer, Videos, Video Detail, Weekly, Automation, Activity and Settings.
Preserve PO Demo and all controlled API/authority semantics. No backend,
database, provider, credential, scheduler, scoring, Note, Weekly, Deep
Analysis, v4 dispatch or TASK-016G work is authorized. Do not add pages,
dependencies, package/lockfile changes, external assets, public hosting,
pushes, tags or releases.

Treat Note/Weekly/Deep Analysis unavailable states and `AMBIGUOUS` as truthful
product states. `AMBIGUOUS` must remain distinct from failure and explain that
the request may have reached a provider and will not automatically retry.

## Completion evidence

Use small presentation primitives and a first-party token layer only where they
reduce inconsistency. Add meaningful focused tests; do not create giant markup
snapshots. Browser-review the PO Demo at 1440×900 and 1280×800, including the
golden video, the AMBIGUOUS event and 2026 W36. Confirm console cleanliness and
that browser network traffic is loopback-only.

Run every validation command in TASK-017. For the canonical scanner, report its
actual nonzero baseline (11 accepted existing findings, zero new findings),
never "PASS". Create a handoff from `handoffs/TEMPLATE.md`, commit the scoped
change, then stop for independent review.
