# TASK-017：FCC-Inspired Product Workspace Presentation Refactor

- Status: `READY`
- Assignee: `Codex Implementer` (Reviewer 由主控在实现提交后指定)
- Base: `main@943e1a73b56aecba988d2bd847f9f3031b2f1752` plus the governance
  authorization commit that introduces this task
- Dependencies: 已批准并已实现的 local product workspace / PO Demo
- Reuse decision: `REFERENCE` — Free Claude Code
  (`Alishahryar1/free-claude-code@0fb3b18ca8a21639ba7d1c2f11901217434eab6b`, MIT)
  may inform presentation principles only. Do not copy source, branding, assets,
  runtime behavior, dependencies, or configuration.

## Objective

Refactor only the presentation layer of the existing local React product
workspace into a restrained, dark, tool-oriented interface inspired by the
current Free Claude Code presentation language while keeping this product's
information architecture and identity unmistakably YouTube Intelligence.

## Authorized scope

- Inspect only Free Claude Code current-`main` presentation-layer source needed
  to understand its tokens, spacing, surface hierarchy, navigation, controls,
  responsiveness, and interaction restraint. Verify its current commit and MIT
  license before implementation.
- Create first-party frontend design tokens and small, coherent presentation
  primitives as warranted by the existing React application.
- Redesign the existing Dashboard, Sources, Source Detail Drawer, Videos,
  Video Detail, Weekly, Automation, Activity and Settings surfaces; preserve
  their existing IA, labels, routes, data contracts and PO Demo.
- Improve keyboard focus, status clarity, readable transcript/report surfaces,
  responsive behavior, and meaningful unavailable/blocked treatment.
- Add focused frontend/UI tests and browser E2E coverage for existing navigation,
  active navigation, semantic status states, drawer, tabs, Demo badge and
  provider qualification presentation.
- Add `docs/FCC_UI_DESIGN_REFERENCE.md` with the upstream repository/commit,
  inspected files, MIT license, ADOPT/ADAPT/REJECT decisions, token mapping and
  attribution decision.

## Frozen product and authority boundaries

The UI must only render existing controlled local API projections. It must not
change backend/database authority, provider qualification, credential
architecture, scheduler semantics, scoring trust, Note authority, Weekly
authority, Deep Analysis gating, v4 dispatch, or `AMBIGUOUS` semantics.

Required truthful states remain: Note V1 `UNAVAILABLE` absent a persisted
authoritative NoteRef association; Note V2 `UNAVAILABLE`; Weekly version
`UNKNOWN` when not provable; Weekly V2 `UNAVAILABLE`; Weekly video linkage
`UNAVAILABLE_IN_CURRENT_AUTHORITY`; and Deep Analysis `BLOCKED` without a
qualified live provider plus PO acceptance. `AMBIGUOUS` must remain visibly
distinct from known failure and state that no automatic retry occurs.

## Explicit exclusions

- No new product pages, navigation IA, APIs, DTO authority, persistence,
  database migration, provider work, credential input/management, scheduler
  behavior, TASK-016G, public hosting/release, package publication, push, tag
  or release.
- No production dependency, package-manager, lockfile or toolchain changes.
- No FCC/Claude/Anthropic names, logos, app icons, assets, unique copy or
  screen-for-screen cloning. If implementation changes from `REFERENCE` to
  substantial source copying, stop for attribution/legal scope review first.
- No external fonts, CDNs, icons, images, analytics or browser requests beyond
  localhost/127.0.0.1 during PO Demo E2E.

## Required validation

Run focused frontend tests, relevant API tests, browser E2E at 1440×900 and
1280×800, full pytest, `uv run --offline mypy src`, `uv run --offline ruff
check .`, frontend typecheck/build, `uv build --offline`, `git diff --check`,
and the canonical security scanner. The scanner's accepted baseline is exit 1
with exactly 11 existing findings and zero new findings; it must never be
reported as PASS. Verify browser console/network output and record zero external
browser network requests.

## Delivery

Implementation occurs only in the dedicated branch/worktree named by the task
prompt. Keep changes scoped to frontend presentation, focused tests and the
design-reference/handoff documents. Commit after validation; do not merge to
`main`, push, tag or release. An independent Reviewer must assess the submitted
diff and evidence before any integration decision.
