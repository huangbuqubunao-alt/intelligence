# Intelligence Trust and Evidence Contract

Status: **APPROVED PRODUCT CONTRACT**
This contract supplements and never lowers TASK-016B/TASK-016C frozen scoring,
provider dispatch, Note, and Weekly authority boundaries.

## 1. Evidence contract

Every substantive product claim is traceable at least as:

```text
Source / Channel → Video → timestamped Transcript evidence
```

Where a timestamp is not safely available, the UI must say so rather than
invent it. Original material is retained; translation, personalized
distillation, and system synthesis have separate identities and labels:

```text
Original → Translation → Intelligence Distillation → System Synthesis
```

Technical/product names may remain original-language. User language governs
reading output, not replacement of the original transcript.

## 2. Claim and source classification

Each central claim must be classified as one of: confirmed fact,
evidence-backed statement, opinion, prediction, rumor/unconfirmed, or system
inference. System synthesis/inference must never render as a source statement.

Each evidence source additionally records a role:

- `PRIMARY_ORIGINAL` — root source or first-party material;
- `INDEPENDENT_VERIFICATION` — independent corroboration or practical test;
- `ANALYSIS_COMMENTARY` — interpretation/opinion;
- `SECONDARY_RELAY` — material that passes on another source.

Official identity does not make every opinion high-confidence. Facts prioritize
root sources; practical effect prioritizes independent validation.

Source Profile is an observation record (type, confirmation/correction history,
evidence habits, domains, observed history), never a permanent trusted/
untrusted badge or numeric reputation score. Historical performance is only one
confidence input and cannot replace claim evidence.

## 3. Independence and novelty

Source count is not independent evidence-chain count. A claim tracks, when
known, its original source/reused source/secondary relay/independent
validation. If independence cannot be established, its state is `UNKNOWN`, not
independent by default.

The product separately labels New Information, Repetition/Reinforcement,
Attention/Popularity, and New Independent Evidence. Popularity has no direct
claim-confidence conversion.

## 4. Confidence and disagreement

Visible confidence is only High, Medium, Low, or Insufficient Evidence. Inputs
may include source role, evidence quality, independent verification,
completeness, freshness, disclosed commercial relationship when evidenced, and
historical source performance. The resulting explanation must name material
reasons and must not fabricate percentages, token counts, or pseudo-scientific
precision.

Cross-source synthesis is one of:

- **consensus** — compatible evidence from meaningfully independent chains;
- **disagreement** — materially conflicting claims/evidence;
- **unresolved** — evidence is insufficient, non-independent, or incomplete.

The system may state which side current evidence better supports and why. It
must preserve the competing claims/evidence and uncertainty rather than
normalizing them into a single fact. Confidence changes create a dated history
event with prior value, reason, and cited evidence.

## 5. Correction lifecycle and propagation

Core Intelligence has semantic lifecycle support for `NEW`,
`PENDING_CONFIRMATION`, `CONFIRMED`, `DISPUTED`, `UPDATED`, and
`INVALIDATED`/`OVERTURNED` (implementation may refine enum names but not erase
these meanings). Every transition keeps time, prior state, reason, and
evidence.

A factual correction may report wrong interpretation, unsupported evidence,
outdatedness, incorrectly merged viewpoints, or other explained reason. It
does not change original Transcript or Evidence; it creates a new
interpretation revision and dependency walk. That walk updates current
Intelligence, Topic state/timeline, Dashboard projections, future Ask, and
current confidence. It identifies every affected downstream asset.

Historical Daily/Weekly snapshots are immutable. They can show a later-
corrected/superseded marker pointing to current state; they are never silently
rewritten.

## 6. Existing frozen authority boundaries

- Current Note V1 is `UNAVAILABLE` without persisted authoritative NoteRef;
  no filename/frontmatter/video-ID inference is permitted. Note V2 cannot
  synthesize authority and remains `UNAVAILABLE` absent natural valid authority.
- Weekly V2 remains `UNAVAILABLE` absent authoritative valid V2 authority.
  Existing reports cannot be relabeled or recomputed by the UI as Weekly V2.
- Scoring UI/read continues through `AuthoritativeScoringReader` /
  `VerifiedScoringRead`; raw score rows/artifacts are not trusted display data.
- Deep Analysis has no qualified live provider: OpenAI live is `0/2` and
  credential blocked, Kimi production is `1/2` at `SCHEMA_INVALID`, and Local
  is unqualified with critical-path search closed. TASK-016G is unauthorized.
- Provider/model actual identity is retained. No silent fallback, automatic
  redispatch after AMBIGUOUS, retry-until-valid, app-side JSON repair,
  first-JSON extraction, fence stripping, or second-LLM repair is allowed.
- Credentials never enter logs, cache identity, provenance, rendered UI, or
  persisted plaintext model configuration.
