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
