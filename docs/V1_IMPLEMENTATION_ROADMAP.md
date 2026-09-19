# V1_IMPLEMENTATION_ROADMAP.md

Status: DRAFT — Product Freeze decisions applied — production implementation in progress; Draft work remains locally/runtime unvalidated unless explicitly recorded
Product: **Intelligence** (Working Product Name)
Document authority rank: **3** — below `PRODUCT_CONSTITUTION.md` and `V1_PRODUCT_SPEC.md`, above the Demo.
Purpose: the production **execution order** for V1.

> This Roadmap prioritizes **engineering reality over Demo polish**. It is not a task ledger; the authoritative task DAG lives in `docs/V1_IMPLEMENTATION_TASK_GRAPH.md` and the gate design in `docs/V1_ACCEPTANCE_GATES.md`. Milestones below sequence the *outcome*, and each must land on **real data** before the next depends on it.
>
> **Anchor.** Baseline verified at commit `41233ee` (2026-09-09), branch `codex/v1-product-ux-repair`. M0 must re-confirm this anchor before any implementation, because the task ledger (`tasks/README.md`) is stale relative to code (migrations 006–014 and TASK-018…027 modules already exist on this branch).
>
> **Hard constraints (apply to every milestone).** No silent provider/model fallback. No silent quality downgrade. No surprise paid cloud call. No fabricated result, confidence, timestamp, or cost. Truthful absence beats fabricated completion.

## Current implementation snapshot — 2026-09-20

This is a **GitHub-static snapshot**, not an acceptance claim. Mergeability, code review, and the presence of tests in a Draft are not substitutes for actually running the required local/runtime validation.

### Active core Draft spine

| PR | Milestone slice | Head |
|---|---|---|
| #15 | M3A explicit current Summary authority | `5656a420b31aa59e0f1e1c43695592f4a5846f3b` |
| #18 | M8A persisted output language + batch freeze | `db65b1309a7ad0e033aa351cdccb47d96e4ca61d` |
| #19 | M3B timestamped key points from trusted Evidence | `810bd245136f9994ee1dac97c16fa21b2be9b2da` |
| #24 | M4C Evidence excerpt/stance authority hardening | `63bbc71a02130462142b5d3d7f2ee2b0e520d0d8` |
| #27 | M5A honest Intelligence validation posture | `ce48d3d08e3610558fe57dff94ccab2aaebebc60` |

### Current bounded branches

- **#32 M5B** — `411be176373f35de3c77544613229f91c6703130`: introduces migration **018** and a durable `SUCCEEDED_NO_NEW_INTELLIGENCE` positive-zero result. It creates no fake Intelligence/revision/card and is never inferred from an empty list. Draft; local validation pending.
- **#28 M10A** — `b9985a34811aa00decb5fcb8711d440f87bc896a`: truthful Backup/Restore readiness surface. Draft; local validation pending.
- **#29 M10B** — `22e74544b9131322dfbb00f8bffee11b13d6ac57`: hardened core backup archive + restore staging on the pre-M5B schema line. Draft; it must be reconciled with schema v18 and M5B quiescence semantics before integrated validation.
- **#30 M2C** — `c3c08f1f795b58acadbe24f48b10a80d841739d4`: progressive Following setup over existing Source/policy/schedule commands. Draft; local validation pending.
- **#31 M7A** — `1ef73cfb91768bb378d6e38876f83e0a6ca6af53`: label-only Topic rename on top of #30. Draft; local validation pending.

### Open authority/integration boundaries

- **M4 source excerpt capture is not complete.** #24 has storage/read/UI plumbing and safe absence behavior, but generic caller text must not become authoritative `source_excerpt`. A trusted source-text capture seam is still required.
- **M5B Source Run integration is not complete.** #32 records a durable positive-zero result, but migration-012 Source Run triggers still equate child completion with raw admitted-Intelligence `SUCCEEDED`. The follow-up must accept the validated M5B sidecar without fabricating an Intelligence admission.
- **M10 + M5B integration is not complete.** #29 currently treats every raw distillation `PENDING` row as active work. A validated M5B sidecar intentionally leaves its legacy raw checkpoint PENDING, so integrated backup quiescence must treat that effective terminal result correctly.
- **Host/runtime proof is still pending** for localhost browser E2E, real YouTube/proxy paths, Ollama/local-model qualification, restart persistence on the active stack, and real-data Backup/Restore.

See `docs/V1_LOCAL_VALIDATION_HANDOFF.md` for the exact validation order and no-duplicate-work rules.
>
> **Real-call authorization (Owner ruling 2026-09-17).** Once the Owner gives **"APPROVED — proceed to production implementation,"** that approval authorizes **non-destructive real YouTube ingestion verification against public sources** as part of implementation and testing — the team should **not** request per-test Owner approval for each public ingestion test. It does **NOT** authorize paid cloud-model calls, surprise billing, credential changes, destructive external actions, external writes, or public distribution. **Paid/cloud use remains explicit opt-in** and live-credential cloud provider tests still require separate explicit Owner authorization.

---

## Milestone index

| ID | Milestone | Launch-critical? |
|---|---|---|
| M0 | Reconfirm Real Baseline | Yes (gate) |
| M1 | Real YouTube Ingestion | Yes |
| M2 | No-YAML Mac GUI / Onboarding | Yes |
| M3 | Content + Summary / Video Notes | Yes |
| M4 | Evidence | Yes |
| M5 | Intelligence | Yes |
| M6 | Local Persistence + Restart | Yes |
| M7 | Lightweight Topic | Yes |
| M8 | Multilingual Real Path | Yes |
| M9 | Search | Conditional (KEEP IF CHEAP) |
| M10 | Backup / Restore | Yes |
| M11 | Optional Low-Cost Items | No (KEEP IF CHEAP) |
| M12 | Golden UI E2E | Yes (gate) |
| M13 | 7-Day Dogfood | Yes (gate) |
| M14 | Public Distribution Readiness (RC) | Gate B (separate) |

Dependency spine: `M0 → M1 → {M2, M3}`; `M3 → M4 → M5 → M7`; `M6` underpins M3–M8; `M8` after M5; `M9/M10/M11` after core chain; `M12` after all MUST-HAVE; `M13` after M12; `M14` after M13.

**Release gates (Owner ruling 2026-09-17, Spec §16c).** Completing **M0–M13** achieves **Gate A — V1 Functional Ready / Private Dogfood & Pilot**, usable for Owner dogfood and controlled/private pilot. **Gate B — Public Distribution Ready** is **M14**: everything in Gate A **plus** resolution of public-release blockers (licensing, redistribution rights, privacy, security-scan blockers, macOS signing/notarization, packaging/distribution obligations, other M0-identified legal/release blockers). **Functional Ready must never be described as Public Release Ready.** macOS signing/notarization belongs to **Gate B only** and does not block core implementation or private Dogfood.

---

## M0 — Reconfirm Real Baseline

**Objective.** Establish authoritative ground truth from the repository before any implementation, so the roadmap starts from verified reality, not from the Demo or stale ledgers.

**In scope.** Inspect repository; verify current real ingestion status; verify production GUI path; verify release blockers; establish the authoritative implementation branch/anchor; reconcile the task ledger (`tasks/README.md`) against actual code/migrations; record the authoritative product↔legacy **vocabulary mapping** (product vocabulary canonical for UX/Specs, legacy names retained internally, no large code rename — Spec §6); enumerate the **Gate B** public-distribution blockers (licensing, redistribution, privacy, security-scan, signing/notarization, packaging).

**Out of scope.** Any production implementation, backend behavior change, or frontend behavior change. Any real provider call.

**Dependencies.** None (entry gate).

**Acceptance criteria.** A written, dated baseline record that states: (a) anchor commit + branch; (b) real YouTube body-read status (`read=0`, unproven); (c) live provider qualification status (none qualified); (d) production GUI execution status (`EXECUTION_GUARD_BLOCKED`, read/config-only); (e) persistence status (offline-verified, real-data backup NOT_RUN); (f) distribution blocker list; (g) authoritative launch status (currently NO-GO). If repository state differs from `V1_PRODUCT_SPEC.md §18`, the newer verified state is documented.

**Stop condition / rollback.** If the baseline contradicts a frozen product contract or reveals an authority-boundary change, STOP and ask the Owner (PO) before proceeding. Read-only milestone: no rollback needed.

---

## M1 — Real YouTube Ingestion

**Objective.** Prove the product can read a **real transcript/subtitle body** from YouTube, repeatably, with truthful failure states.

**In scope.** Real transcript body acquisition; reliable source ingestion; truthful transcript failure states (no-captions, `CONTENT_UNAVAILABLE`, `INVALID_RESPONSE`, rate-limit, offline). The repo's existing local-transcription fallback (audio → local Whisper → normalization/quality gate, with audio cleanup semantics) is the honest no-captions path and is included **only if it does not expand V1 scope**; otherwise a truthful "no transcript available" state suffices for V1 and local ASR moves to V1.x.

**Out of scope.** Summary/Notes/Evidence/Intelligence generation. Provider qualification for the analysis LLM (separate gate). Any bundled-form distribution concern.

**Dependencies.** M0. Per Owner ruling 2026-09-17, once the Owner gives **"APPROVED — proceed to production implementation,"** non-destructive real YouTube body-read verification against **public sources** is authorized for implementation/testing without per-test approval. This does **not** authorize paid cloud calls, credential changes, destructive external actions, external writes, or public distribution (those remain explicitly gated/opt-in).

**Acceptance criteria.** Spec §16 criterion A: real transcript body read succeeds and is repeatable across **at least 3 real channels/sources**, including ≥1 non-Chinese source and ≥1 unreliable-caption source (specific sources are an Owner execution detail per Spec §16b, selected before M13). Every failure mode maps to a truthful, recoverable `ErrorCode` state — no fabricated text, no silent degrade.

**Stop condition / rollback.** If real body reads remain unstable (`INVALID_RESPONSE` / shape-unknown) after authorized attempts, STOP: do not fake ingestion. Escalate to Owner; consider the local-transcription path as the honest fallback and record the blocker. No commit of a "green" ingestion claim without a real body read.

---

## M2 — No-YAML Mac GUI / Onboarding

**Objective.** A normal user can set up and add a first real source entirely through the GUI.

**In scope.** ≤4-step onboarding; add first source (Following) via UI; choose recommended model policy; usable normal-user setup; honest status surfaces; the **first-run sample/seed experience (launch-critical, Spec §14)** — one clearly-marked sample chain (Content→Summary→Evidence→Intelligence→Topic) that never mixes invisibly with real data. Actual sample content is selected during implementation from the allowed source policy (Owner-created / explicitly redistribution-licensed / clearly-marked synthetic; arbitrary third-party YouTube content must not be assumed bundleable).

**Out of scope.** Advanced routing UI, provider diagnostics, capability matrices, admission-rule exposure. Per-Following language override (V1.x).

**Dependencies.** M0; pairs with M1 (source added must be really ingestible). Production GUI must move beyond read/config-only for the onboarding→ingest path (requires lifting `EXECUTION_GUARD_BLOCKED` for the authorized normal path only, under the existing mutation-guard/side-effect-authorization design).

**Acceptance criteria.** Spec §16 criterion B: no CLI/YAML for the normal path. A fresh non-developer can complete onboarding and add a real YouTube source. Default settings are minimal; no internal machinery is surfaced. The first-run sample experience is present, clearly marked as example data, and does not mix invisibly with real data.

**Stop condition / rollback.** If enabling the normal execution path would weaken the runtime side-effect guard or open an unauthorized real-call path, STOP and ask PO. Roll back GUI execution enablement; keep read/config-only.

---

## M3 — Content + Summary / Video Notes

**Objective.** Real content produces a faithful Summary / Video Notes.

**In scope.** Real content records; transcript/text surfacing; one-line summary; key points; timestamp chapters where possible; revisable note model; honest "no notes / insufficient" states.

**Out of scope.** Full-transcript translation (V1.x). Evidence/Intelligence admission (M4/M5).

**Dependencies.** M1 (real transcript), M2 (GUI), M6 (persistence for artifacts).

**Acceptance criteria.** On real ingested content, Summary/Notes render with one-line summary + key points + chapters where available, citing their transcript basis. Missing/weak input yields an honest state, never fabricated notes.

**Stop condition / rollback.** If summary quality depends on an unqualified analysis model, STOP rather than silently degrade; surface "model insufficient" and defer to M5/model policy. Roll back to showing raw transcript only.

---

## M4 — Evidence

**Objective.** Evidence is inspectable, provenance-bearing, positioned, and stance-aware.

**In scope.** Evidence provenance; exact source position/timestamp where safely available; stance (`supporting` / `contradicting` / `conditional` only — "unknown"/"insufficient" are **not** stances but sufficiency/confidence states on a separate axis, never mixed); strength; traceability; original preserved with optional translated presentation (translation ≠ second Evidence record); Evidence display switch (译文/双语/原文).

**Out of scope.** Cross-source independent-chain reasoning beyond V1 honesty (RESERVE_V2). Invented timestamps.

**Dependencies.** M3.

**Acceptance criteria.** Spec §16 criterion D (Evidence portion): every Evidence shows provenance + position-or-honest-absence + stance; contradiction is preserved, not collapsed; system inference never renders as a source statement.

**Stop condition / rollback.** If a timestamp cannot be safely established, the UI must say so — never invent. Stance (`supporting`/`contradicting`/`conditional`) must stay on its own axis, separate from sufficiency/confidence; if a design conflates them, STOP and correct before hard-coding.

---

## M5 — Intelligence

**Objective.** Produce revisable, evidence-cited Intelligence with honest confidence and a real admission threshold.

**In scope.** Admission threshold (retention reasons); cited/revisable Intelligence model (current revision pointer + append-only revisions); honest confidence language; **"no new Intelligence" success state**; contradiction/conditional partitioning; "still needs validation" revisability surface.

**Out of scope.** User feedback learning (V1.x). Advanced confidence/source profiles (RESERVE_V2). Deep Analysis / Investigation activation.

**Dependencies.** M4; a **qualified analysis model**. Per Owner ruling 2026-09-17, **V1 launch must not depend on a cloud Provider** — the local-first V1 must **qualify at least one usable local model path** for its required tasks (this is the launch-critical qualification). Cloud models are optional explicit enhancements; live-credential cloud provider tests remain separately gated and explicit opt-in.

**Acceptance criteria.** Spec §16 criterion C (Intelligence) + criterion D (trust): Intelligence cites Evidence; confidence is bounded language (no invented percentages); a content yielding zero Intelligence renders as a positive success; no admitted Intelligence exists without supporting evidence; unsupported/ambiguous/budget-paused/model-unavailable states remain truthful.

**Stop condition / rollback.** If no **local** model path can be qualified for a required task, **do not fabricate Intelligence and do not silently fall back to cloud** — pause + explain ("本地模型不足以生成可靠洞察") with enable-cloud-once / change-model / retry-later. V1 launch must not be made dependent on a cloud Provider. The trust gate is frozen; retries/fallback/substitution are forbidden without material external change + PO authorization.

---

## M6 — Local Persistence + Restart

**Objective.** The loop persists locally and survives restart without data loss or duplicate expensive work.

**In scope.** SQLite as source of truth; artifact persistence (transcripts, notes, evidence, intelligence, topics); migration verification (forward-only, all-or-nothing, no downgrade); restart-preserves-data; idempotent recovery.

**Out of scope.** Cloud sync, multi-device sync (Future). Real-data backup drill (M10).

**Dependencies.** M0 (migration ledger reconciliation). Underpins M3–M8.

**Acceptance criteria.** Spec §16 criterion F: restart preserves user data; migrations apply all-or-nothing with a verified pre-upgrade backup as the rollback path; no duplicate expensive steps on recovery.

**Stop condition / rollback.** Any destructive migration or authority-boundary change is a STOP-and-ask-PO trigger. Rollback = restore verified pre-upgrade local backup, then a later corrective migration after PO approval.

---

## M7 — Lightweight Topic

**Objective.** Intelligence can be grouped into lightweight Topics showing current understanding.

**In scope.** Basic Topic association; current-understanding view; related Evidence/Intelligence display; simple rename/archive only if cheap.

**Out of scope.** Merge, split, lifecycle automation, complex governance, advanced evolution visualizations (V1.x).

**Dependencies.** M5.

**Acceptance criteria.** Topic groups related Intelligence and shows current understanding + related Evidence/Intelligence. Association never rewrites Intelligence/Evidence identity.

**Stop condition / rollback.** If Topic scope expands toward governance/merge/split, STOP and move the extra scope to V1.x. Keep V1 Topic minimal.

---

## M8 — Multilingual Real Path

**Objective.** English source → Chinese output works on real data with the original preserved.

**In scope.** Source-language auto-detection; one global preferred output language; Summary/Notes/Intelligence/Topic generated in the preferred output language; original Evidence preserved; translation as presentation only.

**Out of scope.** Per-Following language override; full-transcript translation; complex tri-state controls that create UX burden (all V1.x).

**Dependencies.** M5 (Intelligence exists to translate-present).

**Acceptance criteria.** Spec §16 criterion I: chosen output language works on a real non-Chinese source; a translation never creates a second Evidence record; the original excerpt + position stay authoritative.

**Stop condition / rollback.** If output-language generation depends on an unqualified model, STOP per M5 rather than degrade. Roll back to original-language presentation with an honest "translation unavailable" state.

---

## M9 — Search (conditional)

**Objective.** Basic local find across the library, if cheap.

**In scope.** Basic Global Search — **locate existing local knowledge objects and navigate to them**: Following, Content, Evidence, Intelligence, Topic, and Research (if Research exists). Basic search filters (KEEP IF CHEAP).

**Out of scope.** RAG, AI answers, semantic Q&A, external web search, saved search, complex query syntax, advanced relevance ranking. Advanced semantic / RAG search is Future (unless separately validated).

**Dependencies.** M6 (persisted data to search).

**Acceptance criteria.** A user can locate a known Following/Content/Evidence/Intelligence/Topic by keyword locally and navigate to it. Search is **KEEP IF CHEAP** and **does not block launch**; if implementation is not cheap, it is deferred to V1.x.

**Stop condition / rollback.** If search cost threatens the schedule, move to V1.x. Search must never block launch.

---

## M10 — Backup / Restore

**Objective.** Prove backup + restore on **real** data.

**In scope.** Minimal backup/restore; integrity check before restore; corrupt-backup-never-overwrites-current-data; **real-data restore drill**.

**Out of scope.** Cloud backup/sync (Future).

**Dependencies.** M6.

**Acceptance criteria.** Spec §16 criterion G: backup + restore verified on real pipeline data (not just temporary environments). Restore preserves the full loop (Following→Content→Summary/Video Notes→Evidence→Intelligence→Topic). Power-fail/crash/concurrent-writer limitations are honestly documented, not overclaimed.

**Stop condition / rollback.** If the real-data drill cannot run safely, STOP; do not claim backup works. A corrupt/failed restore must leave current data intact.

---

## M11 — Optional Low-Cost Items

**Objective.** Add KEEP-IF-CHEAP value only if it does not threaten the schedule.

**In scope.** Local file / local video / subtitle ingestion; Following Focus; Research Lite (§10 of Spec); basic model cost/usage visibility (with honest `UNKNOWN`); simple Topic suggestions; a **lightweight Home surface** (recent content / new Intelligence / what changed) **only if it cheaply reuses existing Content/Intelligence data** — this is **not** a Brief object or Brief pipeline (a standalone Daily/Weekly Brief system is V1.x).

**Out of scope.** Anything that expands engineering complexity materially — move to V1.x.

**Dependencies.** Core chain (M1–M8) complete and stable.

**Acceptance criteria.** Each included item ships only with honest states and no added launch risk. **Research Lite is included only if bounded and cheap; otherwise it moves to V1.x and never blocks launch.**

**Stop condition / rollback.** Any item whose complexity grows is immediately descoped to V1.x. None of these may jeopardize M12–M14.

---

## M12 — Golden UI E2E

**Objective.** Prove the authoritative Golden UI Path end-to-end for a real normal user.

**In scope.** The full Spec §13 path: install/open → ≤4-step onboarding → add real YouTube source → content → transcript → summary → inspectable Evidence → ≥1 eligible Intelligence → trace claim to source (<10s) → restart → data present. No Terminal, no YAML, no developer assistance.

**Out of scope.** Demo-only future concepts.

**Dependencies.** All MUST-HAVE milestones (M1–M8, M10).

**Acceptance criteria.** The Golden UI Path completes on **real data** by a non-developer, with source-trace in <10 seconds and data surviving restart. Sample/seed experience is clearly marked and never mixes invisibly with real data.

**Stop condition / rollback.** If any step requires Terminal/YAML/developer help, V1 is **not** ready — STOP and fix the offending milestone. Do not paper over with Demo fixtures.

---

## M13 — 7-Day Dogfood

**Objective.** Validate the product as a real, cumulative daily tool used voluntarily by the Owner.

**In scope.** Before M13 the Owner selects **~6–8 genuinely useful real YouTube sources** in the same meaningful domain (specific channel names are **not** frozen by Product Freeze — an execution detail), including ≥1 non-Chinese source, ≥1 unreliable-caption source, and several normal stable sources. The Owner then processes ~30–50 real content items, ~20–30 summaries, targeting 5–8 genuinely useful Intelligence and 2–3 lightweight Topics; and simulates no-caption video, offline, transient network failure, model-too-weak, backup+restore, and a non-Chinese source.

**Out of scope.** Marketing/distribution. Feature expansion.

**Dependencies.** M12.

**Acceptance criteria (success signals).**
- Owner opens the app voluntarily on **≥4 of 7 days**.
- Finds **≥1 Intelligence worth citing / acting on**.
- Can trace it to source in **<10 seconds**.
- No data loss; no surprise cloud spend.
- Failures are understandable and recoverable.
- The product feels **cumulative rather than repetitive**.

**Stop condition / rollback.** If the Owner does not return voluntarily, or data loss / surprise spend occurs, STOP: V1 is not launch-ready. Feed findings back to the responsible milestone; do not proceed to M14.

---

## M14 — Public Distribution Readiness (Gate B / RC)

**Objective.** Resolve the public-release blockers and make a final **public-distribution** go/no-go. This is **Gate B**, distinct from Gate A (V1 Functional Ready / Private Dogfood & Pilot, achieved at M13).

**In scope.** Everything in Gate A **plus**: licensing; redistribution rights; privacy requirements; security-scan blockers; **macOS code signing / notarization**; packaging / distribution obligations; other release/legal blockers identified by M0; SBOM/NOTICE completeness; secrets-scanner disposition; privacy P2 re-review; final public-distribution go/no-go.

**Signing / notarization (Owner ruling 2026-09-17).** macOS signing and notarization belong to the **Public Distribution Gate (Gate B) only**. They do **not** block core production implementation or private Dogfood, and they **must** be resolved before public Mac distribution. Ownership is described as **Release Engineering + Owner Release Approval** (no specific person is invented here).

**Out of scope.** New product features.

**Dependencies.** M13 (Gate A achieved).

**Acceptance criteria.** All `docs/RELEASE_BLOCKERS.md` items are resolved or explicitly accepted by the Owner; license/ownership posture is decided; bundled-form GPL (mutagen) and BPE (o200k_base) redistribution are compliant or excluded; **signing/notarization evidence exists**; secrets-scanner disposition is understood (exit `1` on 11 accepted synthetic fixtures is never reported as "PASS"). A signed **public-distribution** go/no-go is recorded.

**Stop condition / rollback.** Any unresolved blocker keeps **public distribution** at **NO-GO**; Gate A private dogfood/pilot may still proceed independently of Gate B. Private GitHub hosting only; no public Release, no PyPI, no history rewrite without explicit Owner decision. If history is found to contain real credentials, STOP and decide jointly with the Owner.

---

## Cross-milestone gate reminders

**Launch Gate coverage map (Spec §16 A–J → milestones).**
- A Real ingestion → **M1** (repeatability across ≥3 real sources).
- B GUI (no CLI/YAML) → **M2**, verified end-to-end in **M12**.
- C Core processing (Summary/Evidence/Intelligence) → **M3, M4, M5**.
- D Trust (provenance/trace/confidence/contradiction) → **M4, M5**.
- E Failure handling (no-captions/offline/rate-limit/model-too-weak/transient) → truthful states built in **M1, M3, M5**, exercised in **M12** and simulated in **M13**.
- F Persistence (restart preserves data) → **M6**.
- G Backup (real-data restore) → **M10**.
- H Cost/privacy (no hidden paid cloud, local-first default) → enforced by the Hard constraints preamble + **M5** (no silent fallback) and verified in **M13** (no surprise cloud spend).
- I Language (output language on real non-Chinese source) → **M8**.
- J Product usability (understandable without developer) → **M2** (onboarding + sample) and **M12/M13** (a non-developer completes the Golden UI Path and returns voluntarily).

The universal per-task gate still applies to every implementation task: focused TDD green + adversarial cases + handoff with reuse/licence evidence + no frozen core touched + `git diff --check` clean + independent reviewer APPROVE (see `docs/V1_ACCEPTANCE_GATES.md`).
- STOP-and-ask-PO triggers: conflict with a frozen product contract; authority-boundary change; new dependency/credential/provider; destructive migration; V2 activation.
- The canonical security scanner is expected to **exit `1`** on exactly the 11 accepted synthetic fixtures with 0 new findings — this is the honest state and must never be relabeled "PASS/clean."

---

## RESOLVED OWNER DECISIONS (Roadmap-level)

All Roadmap-level Open Owner Decisions were ruled by the Owner on **2026-09-17** and are now **closed**. No Roadmap-level Open Owner Decisions remain.

- **OD-R1 — Real-call authorization timing. RESOLVED.** After the Owner gives "APPROVED — proceed to production implementation," non-destructive real YouTube ingestion verification against public sources is authorized for implementation/testing without per-test approval; paid cloud, billing, credential changes, destructive/external-write actions, and public distribution are NOT auto-authorized (paid/cloud = explicit opt-in). Applied in the Hard-constraints preamble and M1.
- **OD-R2 — Provider qualification path. RESOLVED.** V1 launch must not depend on a cloud Provider; the local-first V1 must qualify at least one usable local model path for its required tasks; cloud models are optional explicit enhancements; local-insufficient → pause + explain, never silent cloud. Applied in M5 (and Constitution §10, Spec §12).
- **OD-R3 — Distribution inside V1? RESOLVED.** Two distinct gates: Gate A Functional Ready / Private Dogfood & Pilot (M0–M13) vs Gate B Public Distribution Ready (M14). Functional Ready must never be described as Public Release Ready. Applied in the milestone index, M14, and Spec §16c.
- **OD-R4 — Signing/notarization ownership. RESOLVED.** Signing/notarization belongs to Gate B (Public Distribution) only, does not block core implementation or private Dogfood, and must be resolved before public Mac distribution; ownership = Release Engineering + Owner Release Approval (no specific person invented). Applied in M14.
- **OD-R5 — Vocabulary rename execution window. RESOLVED.** No large V1 code rename; product vocabulary is authoritative for user-facing UX/Specs and legacy names remain internal, so GUI copy adopts product vocabulary without a code-rename prerequisite. Applied in M0 and Spec §6 / Constitution §2b.
- **OD-R6 — Brief/Weekly execution slot. RESOLVED.** No dedicated Brief object/pipeline in V1, so no Brief milestone is required; a lightweight Home surface reusing Content/Intelligence is an optional KEEP-IF-CHEAP item in M11; a standalone Daily/Weekly Brief system is V1.x. Applied in M11 and Spec §5/§6/§8/§9.
