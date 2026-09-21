# PRODUCT_CONSTITUTION.md

Status: DRAFT — Owner decisions applied 2026-09-17 — WAITING FOR FINAL PRODUCT FREEZE APPROVAL
Product: **Intelligence** (Working Product Name)
Document authority rank: **1 (highest)** — see the authority note immediately below and `V1_PRODUCT_SPEC.md` §19.
Scope of this document: long-lived product rules and non-negotiable principles.
This document intentionally avoids implementation details that are likely to change.

> Authority note. After Owner approval the precedence order is:
> `PRODUCT_CONSTITUTION.md` > `V1_PRODUCT_SPEC.md` > `V1_IMPLEMENTATION_ROADMAP.md` > Demo.
> The Constitution states *why* and *what must always be true*; the Spec freezes *what V1 ships*; the Roadmap orders *how we build it*; the Demo is a *north-star vision*, never a backlog.

---

## 1. Product purpose

Intelligence exists to help a single knowledge worker continuously follow selected sources and turn fragmented, fast-decaying content into **traceable, revisable, cumulative knowledge**.

The product compresses information. It never erases the source. Every judgment the product surfaces must remain walkable back to the original evidence in seconds.

Intelligence is not a summarizer. A summary explains what one piece of content says; Intelligence explains **which evidence-backed judgment deserves long-term tracking**. Producing a complete summary and *no* new Intelligence is a normal, successful outcome.

## 2. Product identity

- Working product name: **Intelligence**. Final commercial brand naming is **not** a V1 implementation blocker and **not** part of the Launch Gate; no rebrand is required before Dogfood or Private Pilot.
- Core positioning: *a local-first, evidence-led intelligence workspace that continuously follows selected sources and turns fragmented content into traceable, revisable, cumulative knowledge.*
- Core differentiation:
  1. **Evidence-first, traceable judgment** — claims are always anchored to cited, positioned source evidence.
  2. **Continuous, cumulative knowledge** — understanding compounds across content and time; it is not a pile of one-off summaries.
  3. **Local-first sovereignty** — the user's data lives on the user's device under the user's control.
- **YouTube is the first real Provider, not the product identity.** The architecture must remain multi-source (Provider-neutral) even though YouTube is the only Provider targeted for qualification in V1. Intelligence must never be positioned to users as "a YouTube summarizer."

## 2b. Product vocabulary (canonical)

The product-facing canonical vocabulary is authoritative for all user-facing UX and Product Specs:

```
Following / 关注 → Content / 内容 → Summary / Video Notes → Evidence
→ Intelligence / 洞察 → Topic / 主题 → Research / 调研
```

- Legacy implementation vocabulary (`Source`, `Video`, `Note`, `Investigation`, `Brief`) **may remain internally** where already established.
- A **large V1 code rename is NOT required**.
- An **explicit mapping** between product vocabulary and legacy implementation vocabulary must be maintained (see `V1_PRODUCT_SPEC.md` §6).
- Where product vocabulary and legacy code vocabulary diverge, **product vocabulary wins for anything the user sees or any Product Spec statement**; legacy names persist only as internal implementation detail.

## 3. Evidence-first principle

1. Evidence is **immutable and source-bound**. It records what a source actually said, in the source's original language, with its provenance and exact position (timestamp / offset) where safely available.
2. Interpretation (Summary, Notes, Intelligence) is **revisable** and must always cite the Evidence it rests on.
3. Evidence and interpretation are separate identities and must remain **visibly separate** to the user.
4. If an exact timestamp / position cannot be safely established, the product says so. It never invents one.
5. Original, translation, extraction, and provenance are distinct identities. A correction adds a new interpretation revision; it never rewrites Evidence content.
6. **Evidence stance is exactly `supporting` / `contradicting` / `conditional`.** "unknown" and "insufficient" are **not** stances — they represent evidence **sufficiency / assessment state / confidence state** where applicable.
7. **Stance and confidence semantics must never be mixed.** Stance describes how a piece of Evidence bears on a claim; sufficiency/confidence describes how strongly the claim is supported overall. They are separate axes and must be modeled and surfaced separately.

## 4. Summary ≠ Intelligence

- **Summary / Video Notes** = faithful distillation of what one piece of Content says (one-line summary, key points, chapters where available).
- **Intelligence** = an evidence-backed, revisable judgment that the system deems worth long-term tracking, with honest confidence and a stated reason for retention.
- A piece of Content may yield a high-quality Summary and **zero** Intelligence. This is success, not failure.
- Intelligence admission is a threshold, not a quota. The product must never manufacture Intelligence to look productive.
- User-facing copy must be able to show "未发现值得长期保留的新洞察 / no new Intelligence worth retaining" as a positive, terminal state.

## 5. Following as input

- **Following** is the user-owned subscription input that drives what gets ingested. It is the entry point of the core chain, not a deliverable itself.
- Following is **bounded delegation**: it carries a trigger, priority, budget, frequency limit, execution record, safe-resume behavior, and an owner.
- External discovery never silently creates a Following. The user controls what is followed, and disabling a Following actually stops its execution (it is not a hidden UI toggle).
- Feedback may adjust learned weights/ranking but must never silently override an explicit user interest, ignore rule, enabled state, schedule, limit, or model selection.

## 6. Intelligence / Topic relationship

- **Intelligence** is the revisable interpretation object. It is the atom of cumulative knowledge.
- **Topic** is a lightweight, user-manageable live grouping of related Intelligence. Membership is an **association, not ownership**: creating, renaming, or archiving a Topic must never rewrite Intelligence or Evidence identity.
- The authoritative core chain is:

  ```
  关注 (Following) → 内容 (Content) → Summary / Video Notes → Evidence → Intelligence → Topic
  ```

- **Research is NOT part of the minimum launch-critical chain.** Research Lite is conditional V1 scope at most (see §13) and must never block launch.
- **No dedicated Brief object or Brief pipeline in V1.** V1 may include a lightweight **Home surface** (e.g. recent content, new Intelligence, what changed) **only if it cheaply reuses existing Content / Intelligence data**. A standalone Daily/Weekly Brief system belongs to **V1.x** and is **not launch-critical**.

## 7. Local-first

- Local-first means **locally persisted by default**, not "never leaves the device." Structured state is the user's local source of truth (SQLite); large text/artifacts live in local files under the app's data directory.
- Any cloud-backed execution must **declare what leaves the device and to which provider** before it happens.
- Backup ≠ cloud sync. A corrupt backup must never overwrite current data; integrity is checked before restore.
- Publishing targets (e.g. an Obsidian Vault) are **one-way outputs**, never a runtime database and never a bidirectional sync. Intelligence retains complete local operating data independent of any publish target.

## 8. User ownership

- The user owns their data, their Followings, their Topics, their model/cost choices, and their deletion decisions.
- Deletion is policy-driven and honest: "stop monitoring" is distinct from "full historical deletion." Deleting evidence must not leave an unsupported "ghost" Intelligence; affected interpretations are recomputed, marked unsupported/disputed/unavailable, or superseded — never silently retained as if still evidenced.
- Destructive, irreversible actions (e.g. delete-all) require explicit second confirmation.
- The frontend is presentation and command-request only. It never reads the database, the vault, credentials, or provider SDKs directly; all authority flows through the local backend.

## 9. Multilingual principles

Three concepts are independent and must never be conflated:

- **UI language** — the language of the product chrome.
- **Source language** — intrinsic to each piece of Content / Evidence; the original is always preserved.
- **Output language** — the language in which Summary / Notes / Intelligence / Topic are generated.

Rules:

1. Source language is automatically detected; the original is preserved.
2. Translation is a **reading aid / presentation layer only**. The original excerpt and its source position stay authoritative.
3. **A translation never creates a second Evidence record.**
4. One global preferred output language governs generated artifacts in V1 (e.g. English source → Chinese Summary / Notes / Intelligence, with the original Evidence preserved).
5. Per-Following output-language override and full-transcript translation are progressive-disclosure / V1.x concerns, not V1 requirements.

## 10. Model / quality trust rules

- Normal users must not need to understand model routing. Default product behavior is: **推荐 (recommended) = 本地优先 (local-first) = 不未经用户同意产生云端费用 (no cloud spend without consent) = 质量不足时暂停并解释，而不是偷偷降级 (pause and explain on insufficient quality, never silently degrade).**
- A model may only be used when it is **AVAILABLE + QUALIFIED + AUTHORIZED/PRODUCTION_ELIGIBLE**. `CONFIGURED ≠ AVAILABLE ≠ QUALIFIED ≠ PRODUCTION_ELIGIBLE`.
- Trust mechanisms are guarantees, **not user-facing switches**. Users cannot override the trust gate to force an unqualified path.
- When no qualified model can safely produce reliable Intelligence, the product shows an honest state such as **"本地模型不足以生成可靠洞察 / the local model is insufficient to produce reliable Intelligence,"** and offers: enable cloud once, change model, or retry later.
- Routing escalates only when policy demands (rule → cheap → standard → strong). The actual provider/model identity used is always recorded.
- **V1 launch must NOT depend on a cloud Provider being available.** The local-first V1 must qualify **at least one usable local model path** for its required tasks.
- **Cloud models are optional enhancement paths**, activated explicitly by the user — never a launch prerequisite and never a silent default.
- If local quality is insufficient for a task: **pause + explain**. Do not silently use cloud.
- Advanced model routing UI belongs behind progressive disclosure / V1.x.

## 11. No silent cloud spend

- The product never silently calls a paid cloud provider.
- The product never silently falls back from local to cloud, never silently switches model, and never silently increases spend.
- A fallback is legal **only** if the user pre-configured that exact approved model/provider.
- Unavailable / quota-exceeded / budget-exhausted conditions **pause the matching step** with a truthful reason; they do not degrade quality, spend more, or fabricate a result. "Functional pause is preferred to hidden degradation."
- **Real-call authorization scope.** Once the Owner gives **"APPROVED — proceed to production implementation,"** that approval authorizes **non-destructive real YouTube ingestion verification against public sources** as part of implementation and testing, without requiring Owner approval for every individual public ingestion test. It does **not** authorize paid cloud-model calls, surprise billing, credential changes, destructive external actions, external writes, or public distribution. **Paid/cloud use remains explicit opt-in.**

## 12. No fabricated confidence

- The product never fabricates a result, a certainty, a cost/token figure, or a confidence precision it does not have.
- Confidence is expressed in honest, bounded language (e.g. High / Medium / Low / Insufficient Evidence), not invented percentages.
- Unknown stays unknown: `UNKNOWN`, `UNAVAILABLE`, `BLOCKED`, `DISPUTED`, `AMBIGUOUS`, and `NOT_PROCESSED` are visible states. Missing data is never rendered as zero.
- Cross-source synthesis preserves **consensus / disagreement / unresolved**; competing claims are preserved, not collapsed. Source count ≠ independent-chain count; unknown independence stays `UNKNOWN`.
- System inference must never be rendered as if it were a source statement.

## 13. Research boundaries

- Research (deep, external, autonomous investigation) is **not** part of the V1 launch-critical chain.
- **Research Lite** may exist in V1 only if it is sufficiently cheap, and only in this bounded form: start from a Topic or Intelligence; scope limited to 我的资料库 (my library) / 当前对象 (current object) / 指定范围 (specified scope); produce one structured, evidence-led result.
- Research Lite must **not** require: research version history, v1/v2 diff, external web exploration, autonomous refresh, or complex scope management.
- If real Research Lite implementation threatens V1 timing, it moves to V1.x. It never blocks launch.

## 14. V1 vs future philosophy

- V1 is judged by **whether a real, usable, local-first intelligence loop works end-to-end for a normal user on real data** — not by how many Demo features exist.
- The Demo is a **north-star product vision**. It may legitimately contain future-facing concepts that are not in V1. When Demo and Spec conflict, the Spec wins.
- Scope discipline: features that expand engineering complexity materially move to V1.x or Future rather than jeopardizing the core loop.
- Progressive disclosure is the default: a first-time user sees very few settings, very few technical terms, and no internal machinery (routing, capability matrices, admission rules, provider qualification, trust internals). Those remain implementation / advanced concerns.
- **Two distinct release gates.** (A) **V1 Functional Ready / Private Dogfood & Pilot** — the real working loop, usable for Owner dogfood and controlled/private pilot. (B) **Public Distribution Ready** — everything in A **plus** resolution of public-release blockers (licensing, redistribution rights, privacy, security-scan blockers, macOS signing/notarization, packaging/distribution obligations, and any other legal/release blockers identified by M0). **Functional Ready must never be described as Public Release Ready.**

## 15. Honest failure behavior

- Every failure produces an **honest, recoverable state**: no-captions, offline, rate-limit, model-too-weak, transient network failure, and permission problems each map to a truthful user-facing state with a real recovery path (retry, change model, enable cloud once, wait, human action).
- Ambiguous external outcomes are terminal and **never auto-retried** into a fake success. Expired work is reclaimed with an audit trail, never faked as complete.
- The product prefers "pause and explain" over "guess and proceed."
- Truthful absence beats fabricated completion, always.

## 16. Product success principle

V1 is successful when a normal Mac user can, **without Terminal, without YAML editing, without developer assistance, without hidden cloud spend, and without silent quality degradation**:

```
install / open the app
→ add a real YouTube source
→ ingest real content
→ obtain transcript / text
→ generate Summary / Video Notes
→ inspect Evidence
→ obtain at least one traceable Intelligence
→ associate it with a light Topic
→ reopen the app later and continue from persisted local data
```

The measure of the product is a **cumulative** body of traceable knowledge the user voluntarily returns to — not the volume of summaries produced.

---

## RESOLVED OWNER DECISIONS (Constitution-level)

All Constitution-level Open Owner Decisions were ruled by the Owner on **2026-09-17** and are now **closed**. No Constitution-level Open Owner Decisions remain.

- **OD-C1 — Object vocabulary authority. RESOLVED.** Product-facing canonical vocabulary (Following/关注 → Content/内容 → Summary/Video Notes → Evidence → Intelligence/洞察 → Topic/主题 → Research/调研) is authoritative for user-facing UX and Product Specs. Legacy implementation vocabulary (Source, Video, Note, Investigation, Brief) may remain internally; **no large V1 code rename is required**; an explicit product↔legacy mapping is maintained. Applied in §2b and `V1_PRODUCT_SPEC.md` §6.
- **OD-C2 — "Brief / Weekly" in V1. RESOLVED.** No dedicated Brief product object or Brief pipeline in V1. A lightweight Home surface reusing existing Content/Intelligence is permitted only if cheap; a standalone Daily/Weekly Brief system is V1.x and not launch-critical. Applied in §6.
- **OD-C3 — Brand name finalization. RESOLVED.** "Intelligence" remains the Working Product Name. Final commercial branding is not a V1 implementation blocker and not part of the Launch Gate; no rebrand is required before Dogfood or Private Pilot. Applied in §2.
