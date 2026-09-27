# V1_PRODUCT_SPEC.md

Status: DRAFT — Owner decisions applied through 2026-09-25 — WAITING FOR FINAL PRODUCT FREEZE APPROVAL
Product: **Intelligence** (Working Product Name)
Document authority rank: **2** — below `PRODUCT_CONSTITUTION.md`, above `V1_IMPLEMENTATION_ROADMAP.md` and the Demo.
Purpose: the authoritative **frozen V1 scope**.

> **Anti-misreading rule.** This Spec exists to make it impossible to interpret the Demo as the full V1 backlog. The clickable Demo (`frontend/demo-v1/`, `frontend/src/demo-v1/`) is a **north-star product vision**. It legitimately contains future-facing concepts (Research/Investigation, Daily/Weekly Brief, per-Following language override, rich Topic evolution, global semantic search) that are **not** V1 commitments. Where the Demo conflicts with this Spec, **this Spec wins**.

---

## 1. V1 goal

Ship a **real, usable, local-first intelligence loop** that works end-to-end for a normal Mac user on **real data**, without Terminal, YAML editing, developer assistance, hidden cloud spend, or silent quality degradation.

V1 is judged by the working loop, **not** by Demo feature count. The authoritative acceptance measure is the **Golden UI Path** (§13) passing on real data, plus the **Launch Gate** (§16) and the **7-Day Dogfood Gate** (§16b).

## 2. Target user

A single knowledge worker (the Owner is the reference user) on macOS / Apple Silicon who:

- wants to continuously follow a handful of meaningful sources in a domain they care about;
- is non-technical enough to refuse Terminal/YAML, but sophisticated enough to judge whether an insight is worth acting on;
- cares about provenance (can this be traced to the source?) and sovereignty (my data stays mine);
- may consume non-Chinese sources but prefer Chinese output.

Single-user. No accounts, no permissions model, no multi-user, no collaboration in V1.

## 3. Primary use cases

1. **Follow & ingest.** Add a real YouTube channel/video as a Following; the product acquires real content and transcript/text.
2. **Understand a piece of content.** Read the Summary / Video Notes (one-line summary, key points, chapters where available).
3. **Verify a claim.** Inspect Evidence with provenance, exact position/timestamp, and stance; trace any Intelligence back to its source in <10 seconds.
4. **Accumulate judgment.** Obtain revisable Intelligence with honest confidence; associate it with a lightweight Topic that shows current understanding.
5. **Return later.** Reopen the app after restart and continue from persisted local data; back up and restore without data loss.
6. **Cross-language.** Consume an English source and read Chinese Summary / Notes / Intelligence while the original Evidence is preserved.

## 4. Core user journey

```
关注 (Following)
→ 内容 (Content)
→ Summary / Video Notes
→ Evidence
→ Intelligence
→ Topic
```

Research is **not** in the minimum launch-critical chain. Research Lite is conditional (§10).

## 5. Information architecture (V1)

Primary navigation the V1 user needs to reach the whole loop:

- **关注 / Following** — manage subscriptions; add a real YouTube source.
- **内容 / Content** — the ingested items and their transcript/text state.
- **洞察 / Intelligence** — Summary/Notes, Evidence, and Intelligence; the trace surface.
- **主题 / Topic** — lightweight groupings of related Intelligence and current understanding.
- **设置 / Settings** — model policy, output language, backup/restore, sample data, honest status.
- **搜索 / Search** — Basic Global Search: locate and navigate to existing local knowledge objects. **KEEP IF CHEAP; does not block launch** (§8, §9).
- **首页 / Home (optional, KEEP IF CHEAP)** — a lightweight surface (recent content, new Intelligence, what changed) **only if it cheaply reuses existing Content / Intelligence data**. This is **not** a Brief object; a standalone Daily/Weekly Brief system is V1.x (§9).

Internal machinery (routing tables, capability matrices, admission rules, provider qualification, trust internals, provider diagnostics) is **not** surfaced to the default user.

## 6. Object definitions (authoritative for V1)

V1 uses the canonical product vocabulary below, which is **authoritative for user-facing UX and Product Specs** (Owner ruling 2026-09-17). Legacy implementation names may remain internally where already established; **no large V1 code rename is required**. This table is the maintained product↔legacy mapping.

| Freeze term | Legacy / code equivalent | V1 definition |
|---|---|---|
| **Following (关注)** | Source / SourceSubscription | User-owned subscription input that drives ingestion. Bounded delegation: trigger, priority, budget, frequency limit, execution record, safe resume, owner. External discovery never silently creates one. |
| **Content (内容)** | Video | Canonical raw-material record for one ingested item, with its transcript/text and processing state. `1 Content → 0..n Evidence`, `0..n Intelligence`. |
| **Summary / Video Notes** | Note V1 / Note V2 | Faithful distillation of one Content: one-line summary, key points, timestamp chapters where possible. Revisable; cites Evidence. |
| **Evidence** | Evidence | Immutable, source-bound record of what a source actually said. Fields: provenance, exact position/timestamp where safely available, original quote (source language), optional translated presentation, strength, **stance**. |
| **Intelligence (洞察)** | Intelligence | Revisable, evidence-backed judgment worth long-term tracking, with honest confidence, retention reasons (admission), and "still needs validation" (revisability). Current revision is a pointer into append-only revision history. |
| **Topic (主题)** | Topic | Lightweight, user-manageable live grouping of related Intelligence. Association, not ownership. |
| **Research / Research Lite** | Investigation | Conditional V1 scope at most (§10). Not launch-critical. |
| **Brief / Weekly** | Brief / Weekly snapshot | **Not a V1 product object** (Owner ruling 2026-09-17). No dedicated Brief pipeline in V1. A lightweight Home surface reusing Content/Intelligence is KEEP IF CHEAP (§5); a standalone Daily/Weekly Brief system is **V1.x**, not launch-critical. |

**Evidence stance (V1) — Owner ruling 2026-09-17:** stance is exactly `supporting`, `contradicting`, `conditional`. **"unknown" / "insufficient" are NOT stances** — they represent evidence **sufficiency / assessment state / confidence state** where applicable, and live on a separate axis. Stance and confidence semantics must never be mixed. (The Demo's "Insufficient Evidence" value is a *confidence/sufficiency* label, not a stance; V1 keeps it on the confidence axis.)

**Evidence provenance & position:** every Evidence carries its originating Content/Following, provider, and the exact source position (timestamp/offset) where safely available; if not safely available, the UI states so and never invents it.

**Intelligence honesty contract:** confidence is bounded language on the **confidence/sufficiency axis** (e.g. 强支持 / 部分支持 / High / Medium / Low / Insufficient Evidence), never invented percentages, and **distinct from Evidence stance** (supporting/contradicting/conditional) — the two axes must not be mixed. Admission requires stated retention reasons. Revisability requires "still needs validation" state. **"No new Intelligence" is a successful processing outcome** and must render positively (e.g. 未发现值得长期保留的新洞察).

## 7. V1 MUST HAVE (frozen)

These are launch-critical. V1 does not ship without all of them working on **real data** — **except** any bullet explicitly marked **KEEP IF CHEAP**, which is conditional and non-launch-blocking (it moves to V1.x if not cheap).

**App & onboarding**
- Mac usable app.
- GUI onboarding, ≤4 steps.
- No Terminal / no YAML requirement for the normal path.
- One sample / seed library experience (§14).

**Real ingestion**
- Real YouTube Provider.
- Real transcript/text ingestion — a real subtitle/transcript **body** is read (not just metadata/enumeration).
- Truthful transcript failure states.

**Core chain**
- Following.
- Content.
- Video Summary / Notes: one-line summary, key points, timestamp chapters where possible.
- Evidence: source provenance, exact source position/timestamp where available, stance (`supporting` / `contradicting` / `conditional`), with evidence sufficiency/confidence kept on a **separate axis** (never mixed into stance).
- Intelligence: honest confidence language, revisable model, "no new Intelligence is a successful outcome."
- Lightweight Topic association.

**Trust & traceability**
- Evidence source provenance.
- Source trace from Intelligence back to original Evidence in **<10 seconds**.
- Contradiction preserved (not collapsed).

**Persistence, backup, sovereignty**
- Local SQLite as source of truth.
- Persistent local state; restart preserves user data.
- Minimal Backup / Restore, **verified on real data**.
- Local-first default.

**Model & cost honesty**
- Simplified model policy (recommended = local-first).
- No silent local→cloud fallback.
- No surprise paid calls.
- Cloud Intelligence requires a separate, affirmative data-and-cost authorization before dispatch; selecting Quality-first is not consent.
- Honest error states; retry / recovery.

**Language**
- One global preferred output language.
- Multilingual source handling; source language auto-detected; original preserved.
- English source → Chinese Summary / Notes / Intelligence.
- Translation as presentation, **not** a second Evidence record.

**Usability**
- A user can understand what the product does without developer explanation.
- **Basic Global Search — KEEP IF CHEAP; does not block launch** (Owner ruling 2026-09-17). V1 search means **locating existing local knowledge objects and navigating to them**: Following, Content, Evidence, Intelligence, Topic, and Research (if Research exists). It must **not** require RAG, AI answers, semantic Q&A, external web search, saved search, complex query syntax, or advanced relevance ranking. If not cheap, it moves to V1.x (§8, §9).

**Data control & deletion honesty**
- Disabling a Following actually stops its execution (not a hidden UI toggle).
- Destructive, irreversible actions (e.g. delete-all) require explicit second confirmation.
- Deleting evidence never leaves an unsupported "ghost" Intelligence: affected interpretations are recomputed, marked unsupported/disputed/unavailable, or superseded.

## 8. V1 KEEP IF CHEAP

Included only if they do not expand engineering complexity materially. **These must NOT block launch.** If cost grows, move to V1.x.

- Local file / local video / subtitle ingestion.
- Following Focus (focus/ignore weighting within a Following).
- Research Lite (§10).
- Basic model cost / usage visibility (with honest `UNKNOWN` where usage is not reliably measurable).
- Simple Topic suggestions.
- **Basic Global Search** — locate + navigate existing local objects; no RAG/AI answers/semantic Q&A/web/saved search/complex syntax/advanced ranking. Does not block launch.
- **Lightweight Home surface** — recent content / new Intelligence / what changed, only if it cheaply reuses existing Content/Intelligence. Not a Brief object.
- Basic search filters.

## 9. V1.x (explicitly deferred)

- Obsidian Publish.
- Standalone Daily/Weekly **Brief** system (Brief object + Brief pipeline). Not launch-critical; the V1 optional Home surface (§5, §8) is not a Brief.
- Research History.
- Research snapshot diff.
- Topic merge / split / lifecycle governance.
- Per-Following output-language override.
- Full-transcript translation.
- Advanced model routing UI.
- Detailed provider diagnostics.
- Following Groups.
- Advanced Following filters.
- Bilibili real integration.
- X (Twitter) real integration.
- User feedback learning.
- Richer cost controls.
- Richer Topic evolution UI.

## 9b. FUTURE (explicitly out of scope beyond V1.x)

- Douyin real integration.
- Xiaohongshu real integration.
- External Deep Research.
- Autonomous external exploration.
- Cloud sync.
- Multi-device sync.
- Team / collaboration.
- Knowledge Graph.
- Complex account system.
- AI chat over the whole library (unless separately validated).
- Advanced semantic / RAG search (unless separately validated).

## 10. Research Lite — conditional V1 definition

Research Lite may exist in V1 **only if cheap**, and only in this bounded form:

- Start from a Topic or an Intelligence.
- Scope limited to: 我的资料库 (my library) / 当前对象 (current object) / 指定范围 (specified scope).
- Produce **one** structured, evidence-led result.

It must **not** require: research version history, v1/v2 diff, external web exploration, autonomous refresh, or complex scope management.

**If real implementation threatens V1 timing, Research Lite moves to V1.x. It never blocks launch.**

## 11. Topic — V1 definition

V1 Topic is lightweight. It should:

- group related Intelligence;
- show current understanding;
- show related Evidence / Intelligence;
- support simple rename / archive **only if cheap**.

It must **not** require: merge, split, lifecycle automation, complex governance, or advanced evolution visualizations. Topic membership is an association and must never rewrite Intelligence/Evidence identity.

## 12. Model strategy — V1

- **Owner ruling 2026-09-25: Local-first does not mean Intelligence must be Local-only.** Ingestion support where applicable, Scoring, Summary / Video Notes, Evidence extraction/binding/validation, persistence, and provenance retain usable local paths. The already qualified local `qwen3:8b` path may continue to serve Scoring and Summary. No local model is currently qualified for V1 Intelligence Distillation.
- Normal users do not configure routing internals. **Recommended / Local-first** is the default: local work proceeds; when no qualified local Intelligence model exists, Intelligence pauses honestly while Summary and Evidence remain readable. It never auto-switches to cloud.
- **Quality-first** may select a qualified high-quality cloud model for Intelligence only after a separate affirmative cloud-data authorization. Scoring and Summary still use their proven local paths. **Cost-first** retains its existing bounded semantics and never implies cloud consent.
- Before any verified Evidence/task context leaves the device, show the exact provider and model, the bounded outgoing data, that original local Evidence remains authoritative, and cost as known, free, estimated, or `UNKNOWN`. The user must explicitly confirm. Consent is not inferred from Recommended, Auto, startup, a local failure, or Quality-first selection. The backend persists the authorization with the provider/model, verified input identity, output language, and execution.
- If the local model cannot reliably produce Intelligence and the user has not authorized cloud, show **"本地模型不足以生成可靠洞察 / the local model is insufficient to produce reliable Intelligence"** with explicit enable-high-quality, supported model-change, and retry-later actions. This is an honest paused/unavailable Intelligence state, not a failed Summary or fabricated positive-zero.
- A cloud model still requires separate quality qualification on real Evidence, including restraint and a semantically valid admitted Intelligence. Admission remains evidence-first and threshold-based; zero Intelligence remains a legal success. No full database, unrelated Content, arbitrary file, or credential is sent. No silent paid call, model substitution, duplicate dispatch, or quality downgrade is allowed.
- Advanced routing lives behind progressive disclosure / V1.x.

## 12b. Multilingual — V1

Keep the architecture distinction (UI language / source language / output language) but simplify the UX.

V1 minimum:
- source language automatically detected;
- source original preserved;
- one global preferred output language;
- Summary / Notes / Intelligence / Topic generated in the preferred output language;
- Evidence can show original + translated presentation (e.g. 译文 / 双语 / 原文 switch);
- translation is not a separate Evidence record.

Moved to V1.x: per-Following language override; full-transcript translation; complex tri-state controls if they create UX burden.

## 13. Golden UI Path (authoritative)

The single end-to-end path that defines V1 usability. No Terminal. No YAML. No developer assistance.

```
Fresh normal user
→ installs / opens app
→ completes ≤4-step onboarding
→ adds one real YouTube source
→ content appears
→ transcript / text is acquired
→ summary appears
→ Evidence is inspectable
→ if cloud Intelligence is chosen, the user explicitly reviews provider/model, outgoing Evidence scope, and cost before authorization
→ at least one eligible Intelligence appears
→ user traces a claim back to source
→ app restarts
→ data remains present
```

## 14. Sample / seed experience

V1 ships a first-run sample experience so a new user understands the product **before** their first real source finishes processing.

- Provide one bundled / licensed / safe sample chain: Content → Summary → Evidence → Intelligence → Topic.
- Clearly mark it as example data.
- The user should understand: "This is how Intelligence will process your own sources."
- Sample data must **not** mix invisibly with real user data.

**Source policy (Owner ruling 2026-09-17).** The sample experience is **required**, but the actual sample content does **not** need to be selected during Product Freeze — selection happens during implementation. Allowed sample sources are:
- Owner-created material;
- material explicitly licensed for redistribution;
- clearly-marked synthetic / demo material.

Do **not** assume arbitrary third-party YouTube content may be bundled.

## 15. Failure UX

Every failure mode produces an honest, recoverable state — never a fake success, never a silent degrade:

| Failure | Required honest behavior |
|---|---|
| No captions / transcript unavailable | Truthful "no transcript" state; offer local transcription path or wait; never fabricate text. |
| Offline | Truthful offline state; pause; safe resume; no retry-until-success loop. |
| Rate limit | Honor backoff/`Retry-After`; show waiting state. |
| Model too weak / not qualified | "本地模型不足以生成可靠洞察"; offer enable-cloud-once / change model / retry later. |
| Transient network failure | Bounded retry with truthful status; terminal failure stays visible. |
| Ambiguous external outcome | Terminal, never auto-retried into false success. |

## 16. Acceptance criteria (Launch Gate)

V1 is **NOT** launch-ready unless **all** are true on **real data**:

- **A. Real ingestion** — real transcript body read succeeds; repeatable across at least 3 real channels/sources.
- **B. GUI** — no CLI/YAML for the normal path.
- **C. Core processing** — Summary, Evidence, Intelligence all produced.
- **D. Trust** — Evidence provenance; timestamp/source trace; honest confidence; contradiction preserved.
- **E. Failure handling** — no-captions, offline, rate-limit, model-too-weak, transient failure all produce honest recoverable states.
- **F. Persistence** — restart preserves user data.
- **G. Backup** — backup + restore verified on real data.
- **H. Cost/privacy** — local-first default; no cloud request before explicit provider/model, data-scope, and cost disclosure/confirmation; no hidden paid call or silent fallback.
- **I. Language** — chosen output language works on a real non-Chinese source.
- **J. Product usability** — a user can understand what the product does without developer explanation.

## 16b. 7-Day Dogfood Gate (Owner)

Beyond the Launch Gate, V1 requires an explicit 7-day Owner dogfood on **real data**. This is an authoritative acceptance measure owned by the Spec; `V1_IMPLEMENTATION_ROADMAP.md` M13 executes it.

**Baseline setup.**
- Follow ~6–8 real YouTube channels in the same meaningful domain. **Specific channel names are NOT frozen by Product Freeze** (Owner ruling 2026-09-17); the Owner selects ~6–8 genuinely useful real sources **before M13**.
- The set should include: at least 1 non-Chinese source; at least 1 unreliable-caption source; several normal stable sources.
- Specific channel selection is an **execution detail**, not a Product Freeze blocker.

**Processing volume (approximate).**
- 30–50 real content items.
- 20–30 summaries.
- Target 5–8 genuinely useful Intelligence.
- 2–3 lightweight Topics.

**Simulations.** No-caption video; offline; transient network failure; model-too-weak; backup + restore; a non-Chinese source.

**Success signals.**
- Owner opens the app voluntarily on ≥4 of 7 days.
- Finds at least 1 Intelligence worth citing / acting on.
- Can trace it to source in <10 seconds.
- No data loss; no surprise cloud spend.
- Failures are understandable and recoverable.
- The product feels cumulative rather than repetitive.

If the Owner does not return voluntarily, or data loss / surprise spend occurs, V1 is **not** launch-ready.

## 16c. Two release gates (Functional Ready vs Public Distribution Ready)

Owner ruling 2026-09-17. There are **two distinct release gates**. The §16 Launch Gate + §16b Dogfood Gate define **Gate A only**.

> Label note: "Gate A / Gate B" in this section are the two **release gates**. They are distinct from the §16 acceptance-criteria letters **A–J**, which are individual functional criteria (referenced elsewhere as "Spec §16 criterion X").

**Gate A — V1 Functional Ready / Private Dogfood & Pilot.** Requires:
- real working ingestion;
- normal-user GUI;
- Summary;
- Evidence;
- Intelligence;
- persistence;
- honest failures;
- real-data Backup / Restore;
- multilingual required path;
- Golden UI Path;
- 7-Day Dogfood.

This state may be used for **Owner Dogfood and controlled/private pilot**.

**Gate B — Public Distribution Ready.** Requires **everything in Gate A PLUS** resolution of public-release blockers:
- licensing;
- redistribution rights;
- privacy requirements;
- security-scan blockers;
- macOS signing / notarization;
- packaging / distribution obligations;
- other release/legal blockers identified by M0.

**Do NOT describe Functional Ready as Public Release Ready.** macOS signing/notarization belongs to Gate B and does not block core implementation or private Dogfood.

## 16d. Real-call authorization scope

Owner ruling 2026-09-17. Once the Owner gives **"APPROVED — proceed to production implementation,"** that approval authorizes **non-destructive real YouTube ingestion verification against public sources** as part of implementation and testing. The team should **not** request Owner approval for every individual public YouTube ingestion test.

That approval does **NOT** automatically authorize:
- paid cloud-model calls;
- surprise billing;
- credential changes;
- destructive external actions;
- external writes;
- public distribution.

**Paid/cloud use remains explicit opt-in.**

## 17. Explicit non-goals (V1)

- Not a general YouTube/video summarizer product identity.
- Not a cloud service; no accounts, no multi-user, no collaboration, no sync.
- Not an autonomous external research agent.
- Not a Knowledge Graph / RAG platform.
- No public distribution commitment in V1 itself — V1 Functional Ready (Gate A, §16c) is **not** Public Distribution Ready (Gate B). Distribution/license/redistribution/privacy/security-scan/signing/notarization/packaging belong to Gate B (see `V1_IMPLEMENTATION_ROADMAP.md` M14 and `docs/RELEASE_BLOCKERS.md`).
- No Demo-only feature becomes a V1 commitment merely because it appears in the Demo.

---

## 18. Reality Gap (mandatory honest acknowledgment)

The Spec is a target, not a claim of current state. As of anchor commit `41233ee` (2026-09-09), branch `codex/v1-product-ux-repair`, verified from the repository:

- **Demo is fixture-driven.** `frontend/src/demo-v1/` never calls `/api`, invokes no cloud/local model, writes no SQLite, creates no backup, and restores nothing. All content comes from `fixtures.ts`. The Demo carries the "Intelligence" brand and the Following/Content/Evidence/Intelligence/Topic/Research IA, but it is a **vision prototype**, not a working product.
- **Real YouTube ingestion has never read a real subtitle/transcript body.** The furthest real smoke result is `metadata=1 / enumerate=1 / read=0` (directory enumeration only). Body reads are always zero; several real samples returned `INVALID_RESPONSE` / `CONTENT_UNAVAILABLE`. A real four-phase body-read smoke is **NOT AUTHORIZED / NOT EXECUTED** (`docs/SMOKE_AUTHORIZATION_MATRIX.md`). Real ingestion is **unproven**, not merely untested at scale.
- **No live analysis provider was qualified at this historical anchor.** OpenAI adapter was live-credential-blocked (`0/2`); Kimi/Moonshot production adapter was `1/2` (`SCHEMA_INVALID`); local Ollama was unqualified. The provider-qualification gate was frozen (`docs/LIVE_PROVIDER_QUALIFICATION_PREREQUISITE.md`). The 2026-09-17 local-only launch interpretation is superseded for Intelligence by the 2026-09-25 Owner ruling in §12; this dated baseline does not describe current M12 qualification.
- **The production GUI is real but read/config-only.** `frontend/src/workspace/App.tsx` connects to a real loopback backend (`127.0.0.1:8765`, `youtube-intel serve-api`), but real execution is fail-closed behind a runtime side-effect guard: `POST /sources/{id}/check`, weekly generation, and Deep Analysis return `EXECUTION_GUARD_BLOCKED` (`src/youtube_intel/orchestration_service.py`). There is no credential/API-key input; Deep Analysis is hard-blocked. The production workspace still presents the **older** "YouTube Intelligence Agent" IA, not the Demo IA.
- **M10 real-data core Backup / Restore now passes.** The controlled drill on an isolated clone of persisted pipeline data verifies SQLite + referenced Intelligence-owned DATA, explicit restart-boundary confirmation, rollback and corrupt-archive safety, M8 translation survival, and Vault exclusion. Physical power-loss behavior was not simulated. See [`docs/M10_BACKUP_RESTORE_ACCEPTANCE.md`](M10_BACKUP_RESTORE_ACCEPTANCE.md). This updates the M10 evidence only; the overall release remains **NO-GO** until its independent gates pass.
- **Public distribution is blocked.** No open-source license (proprietary `NOTICE`, pseudonymous owner); `mutagen` GPL-2.0-or-later blocks bundled forms; `o200k_base.tiktoken` BPE redistribution is class C (no downstream grant); secrets scanner exits `1` on 11 accepted synthetic fixtures; residual privacy P2 (historical absolute paths + commit identity). **macOS code signing / notarization is not addressed anywhere** — a genuine gap.
- **Authoritative launch status is NO-GO** (`docs/RELEASE_CHECKLIST.md`, `docs/PROJECT_STATUS.md`, `docs/RELEASE_SIGNOFF.md`). An older `docs/RC_CHECKLIST.md` snapshot (2026-08-11) reads optimistically but its own differentiated table still concludes public distribution = NO and production deployment = NO.

**Roadmap consequence:** implementation must start by **reconfirming current truth from the repository** (M0), and if repository state has changed since the last product review, document the newer verified state before proceeding.

## 19. Document authority

After Owner approval:

```
PRODUCT_CONSTITUTION.md
>
V1_PRODUCT_SPEC.md
>
V1_IMPLEMENTATION_ROADMAP.md
>
Demo
```

If the Demo conflicts with `V1_PRODUCT_SPEC.md`, **the Spec wins**. The Demo may contain future-facing concepts not in V1.

## 20. Change discipline

No new requirements may be silently invented. Anything important not covered here must be recorded by **creating a new OPEN OWNER DECISIONS section** for Owner ruling, and is not decided unilaterally unless required for document consistency. As of the Owner ruling of 2026-09-17, all previously open items are **resolved** (see RESOLVED OWNER DECISIONS below).

---

## RESOLVED OWNER DECISIONS (Spec-level)

Spec-level Owner Decisions were ruled through **2026-09-25** and are now **closed**. No Spec-level Open Owner Decisions remain.

- **OD-S1 — Vocabulary rename scope. RESOLVED.** Product vocabulary is authoritative for user-facing UX and Specs; legacy code names may remain internally; **no large V1 code rename required**; mapping maintained. Applied in §6 (and Constitution §2b).
- **OD-S2 — Brief / Weekly in V1. RESOLVED.** No dedicated Brief object/pipeline in V1; optional lightweight Home surface only if it cheaply reuses Content/Intelligence; standalone Daily/Weekly Brief = V1.x. Applied in §5, §6, §8, §9.
- **OD-S3 — `insufficient` as stance vs confidence. RESOLVED.** Stance = `supporting`/`contradicting`/`conditional` only; "unknown"/"insufficient" are sufficiency/assessment/confidence states, never stances; the two axes must not be mixed. Applied in §6, §7.
- **OD-S4 — Sample library licensing. RESOLVED.** Sample experience remains required; actual content is selected during implementation, not at freeze; allowed sources = Owner-created / explicitly redistribution-licensed / clearly-marked synthetic; arbitrary third-party YouTube content must not be assumed bundleable. Applied in §14.
- **OD-S5 — Dogfood source selection. RESOLVED.** Specific channel names are not frozen now; Owner selects ~6–8 real sources before M13 (≥1 non-Chinese, ≥1 unreliable-caption, several stable); an execution detail, not a freeze blocker. Applied in §16b.
- **OD-S6 — Global search. RESOLVED.** Basic Global Search remains **KEEP IF CHEAP** and non-launch-blocking; scope = locate + navigate local objects; no RAG/AI answers/semantic Q&A/web/saved search/complex syntax/advanced ranking. Applied in §5, §7, §8, §9.
- **OD-S7 — Distribution in V1 scope. RESOLVED.** Two distinct gates: Gate A Functional Ready / Private Dogfood & Pilot vs Gate B Public Distribution Ready (adds licensing, redistribution, privacy, security-scan, signing/notarization, packaging, other M0-identified blockers). Functional Ready must never be described as Public Release Ready. Applied in §16c, §17.
- **OD-S8 — Task-specific local-first model strategy. RESOLVED 2026-09-25.** Qualified local Scoring and Summary plus local Evidence authority remain required. Intelligence may use a separately qualified, explicitly authorized cloud model when no local Intelligence model meets the existing admission threshold. Quality-first selection never implies consent; exact provider/model, bounded Evidence scope, and cost status must be disclosed and confirmed before dispatch. This supersedes the 2026-09-17 local-only Intelligence launch interpretation. Applied in §§7, 12, 13, and 16.
