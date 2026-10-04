# V1.x Phase 11 — creator Following

Owner-authorized continuous task; sole executor, no delegated implementation.
Baseline: `bda7e3eeeaf7f71ab243a82bd75dc4995825d06b`, schema 33.
Branch: `chatgpt/v1x-bilibili-following`.

Done criteria and validation: the owner's complete Phase 11 goal, including
durable baseline, bounded incremental discovery, portable authority, bilingual
Following UI, adversarial/regression/browser checks, fresh review and local commits.
Scope: existing Following, Source Runs, provider adapter, Content publisher,
restore validation, source-health Delta, related frontend, tests and documentation.
Migration 034 is expressly authorized if necessary; schema 33 disallows creators
and does not record portable observed identities or incomplete discovery.

Reuse: DIRECT existing Source Run worker, Following sources, source_video_links,
Content provider, public HTTPS budget, transcript/Summary/Evidence, Research/Delta.
ADAPT provider dispatch and creator projection. REJECT parallel Bilibili feed,
cookies/accounts, anti-abuse bypass, OS scheduler, unqualified acoustic/model paths.

Execution slices: audit/contract; provider identity; durable tracking; worker/API;
frontend; adversarial/restore/product validation; regression/review/remediation;
fresh acceptance/local completion. No merge, push, PR, dependency/toolchain changes.

Completed: creator Following, atomic incremental tracking, public Content/captions,
portable restart/restore state, truthful health and bilingual UI. Final acceptance:
3,550 backend passes / one inherited tokenizer-resource skip; 181 frontend passes;
typecheck/build/static/design/database checks passed; nine online and eight offline
creator browser flows plus 32 prior-phase browser scenarios passed. Three review
passes and fresh complete-diff acceptance resolved all P0/P1/material Phase 11 P2.
Evidence: [Phase 11 acceptance](../docs/validation/phase11/ACCEPTANCE.md).
Protected worktrees preserved; local branch commits only. Production ASR/DA NONE.
