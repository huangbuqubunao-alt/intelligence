# Release Governance Human-Gate Audit

## Status, scope, and non-effect

- **Audit baseline:** `main@e9c5109` (2026-08-31); worktree was clean.
- **Current authoritative release state:** **NO-GO**. This audit neither changes
  that state nor authorizes a push, tag, public release, real Provider call,
  real Vault access, launchd registration, or other operational action.
- **Current posture audited:** personal project; private, proprietary,
  controlled first-party source/wheel/sdist only. Public source/PyPI, bundles,
  containers, installers, app stores, and third-party commercial distribution
  are outside the current authorization.
- **Audit non-effect at `026e9b8`:** human gates closed `0`; signatures
  fabricated `0`; release policy changed `NO`. The audit was a decision package
  for the Product Owner (PO), not itself a waiver or approval.

## Product Owner policy adoption — 2026-08-31

The Product Owner explicitly accepted the finite policy decision proposed by
this audit on baseline `main@026e9b8`: for the current personal, private,
proprietary, controlled first-party source/wheel/sdist posture, use a
trigger-based human-governance profile. This is the authoritative trace for the
policy updates in the release records; it is not a fabricated signature or a
claim that a separate reviewer read any evidence.

The adoption changes only organizational-role ceremony. It preserves every
technical review and its evidence, the canonical scanner's exit `1` and exact
11-fixture disposition, the privacy P2 broader/public-source re-review trigger,
and all explicit PO authority. It does not authorize provider work, TASK-016G,
operational actions, broader distribution, a push, a tag, or a release.

| Gate | Previous audit recommendation | Current controlled-posture disposition | PO authority / future trigger |
| --- | --- | --- | --- |
| `G-SEC` | `DEFER_TO_TRIGGER` | Named independent Security Reviewer is **DEFERRED / NOT REQUIRED NOW**; ADR-008 technical evidence remains required and approved. | Re-evaluate for public/broader source or package distribution, commercial/customer/contractual use, material cloud/credential change, or externally imposed requirement. |
| `G-PRIV` | `DEFER_TO_TRIGGER` | Named independent Privacy Reviewer is **DEFERRED / NOT REQUIRED NOW**; Vault/template technical evidence remains required and approved. | Re-evaluate for public/broader source or package distribution, commercial/customer/contractual use, real-Vault/template/build-boundary change, or externally imposed requirement. |
| `G-RISK` | `KEEP_NOW` | **RETAINED.** | PO must accept or reject at-most-once residual risk. |
| `G-OPS-RECOVERY` | `REDEFINE` | Separate QA/TL signature is **DEFERRED**; the real drill remains unrun and requires explicit PO scope, rollback, and evidence authorization. | Real operational validation; multi-developer team; external customer. |
| `G-OPS-SMOKE` | `KEEP_NOW` | **RETAINED.** | PO authorization remains required per real-smoke phase. |
| `G-OPS-VAULT` | `KEEP_NOW` | **RETAINED.** | PO authorization remains required for real Vault or launchd action. |
| `G-PO-OUTPUT` | `KEEP_NOW` | **RETAINED.** | A qualified live provider and real output remain prerequisites for PO acceptance and TASK-016G authorization. |
| `G-FINAL` | `REDEFINE` | Four-role PO/TL/QA/Privacy table is **DEFERRED / NOT REQUIRED NOW**. A future release still needs all non-deferred technical gates plus any explicit PO release/distribution decision. | Re-evaluate for public/broader distribution, commercial/customer/contractual use, or multi-developer team. |
| `G-SCANNER-EXCEPTION` | `KEEP_NOW` | **UNCHANGED.** | The exact finite 11-fixture PO/TL disposition remains the only accepted exception; any new finding or scope change needs a new PO decision. |
| `G-OWNER` | `KEEP_NOW` | **UNCHANGED.** `墨竹` remains a pseudonymous owner-attribution identifier. | Re-evaluate for broader/public distribution, legal-entity transfer, IP assignment, or copyright registration. |
| `G-LEGAL-FUTURE` | `DEFER_TO_TRIGGER` | **DEFERRED.** No current legal counsel, verified identity, entity, registration, or assignment is introduced. | Public/package release, commercial/contractual distribution, bundle/container/installer/app store, legal-entity transfer, IP assignment, copyright registration, or an externally imposed requirement. |

At a trigger, the PO must determine which review roles and legal/security/privacy
controls are actually applicable to that governing context; the trigger model
does not require every role indiscriminately.

## Method and authority test

The audit read the current release documents, relevant ADRs, TASK-014/TASK-016
records, licensing package, scanner disposition, technical Security/Privacy
reviews, and Git history/blame. A requirement was classified as external only
when repository evidence identified a concrete applicable authority.

The reviewed records identify no statute, regulation, customer contract,
platform policy, organizational policy, certification framework, or adopted
external standard requiring a named Security Reviewer, Privacy Reviewer, TL,
QA, legal counsel, or final-signature table for the current controlled target.
License and rightsholder facts can create obligations for a future selected
distribution mode, but the repository does not establish a present external
human-signature obligation for source/wheel/sdist. This is a repository-evidence
finding, not legal advice.

`d668c6d` (`chore: prepare release candidate validation artifacts`) first added
the Security/Privacy review, at-most-once, operational-authorization, and final
role-signature sections in `docs/RELEASE_BLOCKERS.md`. Its message calls these
"items requiring human decision" but cites no external authority or PO decision
record. The role model therefore has a documented **internal RC-template /
conservative-governance origin**. That does not prove its author used an agent,
so this audit uses "conservative" rather than asserting an unrecorded identity
or intent.

## Inventory and decision matrix

**Count:** 11 material human-governance controls were found at the audit
baseline: 9 then open or conditional and 2 already-recorded decisions.
**External requirements now:** 0. All 11 are project-internal for the current
posture; 4 have a conservative
RC-template origin without a specific PO decision citation (`G-SEC`, `G-PRIV`,
`G-OPS-RECOVERY`, `G-FINAL`).

| Gate | Current status and wording | Origin / first commit | External authority | Purpose and evidence | Current-posture applicability | Future trigger | Recommendation | PO decision required? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `G-SEC` Independent Security Reviewer | OPEN. A Security Reviewer must confirm the ADR-008 SDK/process/credential boundary ([RELEASE_BLOCKERS §2.1](RELEASE_BLOCKERS.md#21-cloud-sdk-isolation-verification), lines 127-144). | Internal RC template; `d668c6d`, `chore: prepare release candidate validation artifacts`; technical evidence added `195167a`. | **Not established.** | Independent review is intended to challenge SDK isolation and secret handling. ADR-008 technical review, scanner regression, offline socket-deny, credential, BPE, and provider-boundary tests already provide objective evidence. | The assurance remains valuable, but a named independent human is an internal governance choice, not demonstrated as required for this private target. | `PUBLIC_SOURCE_RELEASE`, `PUBLIC_PACKAGE_RELEASE`, `COMMERCIAL_DISTRIBUTION`, `EXTERNAL_CUSTOMER`, or material credential/cloud-boundary change. | `DEFER_TO_TRIGGER` | Yes — policy change only. |
| `G-PRIV` Independent Privacy Reviewer | OPEN. A Privacy Reviewer must confirm no Vault/user/template content enters artifacts ([RELEASE_BLOCKERS §2.2](RELEASE_BLOCKERS.md#22-vault--template-distribution-boundary), lines 148-165). | Internal RC template; `d668c6d`; technical evidence added `e9c5109`. | **Not established.** | Independent challenge of user-content and artifact boundary. `VAULT_TEMPLATE_PRIVACY_REVIEW.md` documents fixed templates, anchored runtime Vault writes, fresh archive inspection, sentinels, and credential/log/cache checks. | Named independent review is an internal choice for the current private target; it is not a substitute for the technical boundary, which remains required. | `PUBLIC_SOURCE_RELEASE`, `PUBLIC_PACKAGE_RELEASE`, `COMMERCIAL_DISTRIBUTION`, `EXTERNAL_CUSTOMER`, or any real-Vault/template/build-policy change. | `DEFER_TO_TRIGGER` | Yes — policy change only. |
| `G-RISK` PO at-most-once acceptance | BLOCKED. PO must accept or reject the three residual crash windows ([RELEASE_BLOCKERS §2.3](RELEASE_BLOCKERS.md#23-at-most-once-risk-acceptance), lines 167-177). | Internal architecture/release policy; `d668c6d`. | **Not established.** | Preserves owner authority over a genuine product reliability trade-off; automated evidence cannot choose the acceptable loss/duplication semantics. | **Internally required now** under current policy before claiming release readiness; not ceremonial even for one owner. | Any enablement/use of the affected Provider→SQLite, note replace→SQLite, or audio-cleanup paths. | `KEEP_NOW` | **Yes.** |
| `G-OPS-RECOVERY` Real backup/recovery authorization | BLOCKED. QA+TL authorization is required for controlled real-environment drill ([RELEASE_BLOCKERS §3.1](RELEASE_BLOCKERS.md#31-backup--recovery-drill-real-environment), lines 181-191). | Conservative RC template; `d668c6d`. | **Not established.** | Prevents unsanctioned handling of real pipeline data/Vault state. Automated temporary-environment drill evidence is distinct. | The authorization is meaningful when the drill is run, but a separate QA/TL role is not structurally established for a one-owner project. | `REAL_OPERATIONAL_VALIDATION`, `MULTI_DEVELOPER_TEAM`, `EXTERNAL_CUSTOMER`. | `REDEFINE` — require explicit owner authorization plus recorded scope/rollback and evidence; do not invent QA/TL identities. | **Yes**, before the drill. |
| `G-OPS-SMOKE` PO real-smoke authorization | NOT AUTHORIZED. Each real-smoke phase requires written PO approval, bounded data/cost/retention ([SMOKE_AUTHORIZATION_MATRIX](SMOKE_AUTHORIZATION_MATRIX.md), lines 3-20; [RELEASE_BLOCKERS §3.2](RELEASE_BLOCKERS.md#32-four-phase-real-smoke-authorization)). | Internal safety policy; matrix introduced `8c35cd0` (`docs: add release readiness phase A materials`). | **Not established.** | Owner approval controls network, media/model, cost, and data exposure. | **Internally required when running** real smoke; it is not a signature prerequisite for purely offline technical evidence. | `REAL_OPERATIONAL_VALIDATION`. | `KEEP_NOW` | **Yes**, per phase. |
| `G-OPS-VAULT` PO real-Vault / launchd authorization | NOT AUTHORIZED. Explicit PO scope and rollback approval are required ([RELEASE_BLOCKERS §3.3](RELEASE_BLOCKERS.md#33-real-vault--launchd-authorization), lines 204-210). | Internal safety policy; `d668c6d`. | **Not established.** | Protects user data and system configuration from a materially external side effect. | **Internally required when performing** either action; does not need a separate organizational signature for offline package builds. | `REAL_VAULT_USE`, `LAUNCHD_REGISTRATION`, `EXTERNAL_CUSTOMER`. | `KEEP_NOW` | **Yes**, per action. |
| `G-PO-OUTPUT` PO real Deep Analysis output acceptance | BLOCKED. A qualified live Provider and real qualified-provider Note V2/Weekly V2 output need explicit PO acceptance before TASK-016G ([provider gate status](TASK-016-REFERENCE-PROVIDER-GATE-STATUS.md), lines 8-19). | Product/task authority; current consolidation `05ceb22d` (`docs(task016): consolidate reference provider gate status`), with the acceptance condition introduced in `c94181f`. | **Not established.** | Product owner decides whether real output meets product intent; tests cannot make that product judgment. | **Internally required now** for TASK-016G; it must not be waived by a release-governance simplification. | `TASK-016G_AUTHORIZATION`. | `KEEP_NOW` | **Yes.** |
| `G-FINAL` PO/TL/QA/Privacy final table | BLOCKED. All four roles must sign GO ([RELEASE_BLOCKERS §4.1](RELEASE_BLOCKERS.md#41-po--tl--qa--privacy-reviewer-signatures), lines 212-220; [RELEASE_CHECKLIST](RELEASE_CHECKLIST.md), lines 1-4 and final table). | Conservative RC template; gate text `d668c6d`, table originated `8c35cd0`; final NO-GO roll-up `440c22e`. | **Not established.** | A release roll-up intended to provide separation of duties and evidence review. | Redundant as a multi-role ceremony in a one-owner project unless PO deliberately retains it. It is a roll-up, not a technical test. | `MULTI_DEVELOPER_TEAM`, `PUBLIC_*`, `COMMERCIAL_DISTRIBUTION`, `EXTERNAL_CUSTOMER`. | `REDEFINE` — current profile should use one authenticated owner release decision after objective gates; stricter profiles can restore role separation. | **Yes.** |
| `G-SCANNER-EXCEPTION` Finite PO/TL scanner disposition | **ACCEPTED / CLOSED** for the exact 11 fixtures; scanner still exits `1` and is not PASS ([RELEASE_SIGNOFF](RELEASE_SIGNOFF.md), line 27; `35c22ac`). | Explicit recorded internal PO/TL policy decision; `35c22ac`, `docs(release): accept finite scanner fixture disposition`. | **Not established.** | Bounds a known scanner false-positive matrix without weakening scanner behavior. | Applies now only to the fixed controlled source/wheel/sdist matrix. | Any new finding, scanner-policy change, broader distribution, or fixture change. | `KEEP_NOW` — preserve the finite scope. | Already made; new trigger requires a new PO decision. |
| `G-OWNER` Owner attribution and controlled distribution posture | **ACCEPTED / CLOSED**. PO/TL selected private/proprietary controlled source/wheel/sdist; `墨竹` is pseudonymous first-party attribution ([license package](LICENSE_DISTRIBUTION_DECISION_PACKAGE.md), §§Status and First-party owner attribution). | Explicit recorded internal decision; `d493691`, `docs(release): record first-party owner attribution`. | **Not established for current posture.** | Defines the current artifact boundary without fabricating verified legal identity. | Applies now and is already resolved for the stated current target. | `PUBLIC_*`, `COMMERCIAL_DISTRIBUTION`, `LEGAL_ENTITY_TRANSFER`, `COPYRIGHT_REGISTRATION`. | `KEEP_NOW` — retain its narrow scope. | Already made; broadened scope requires a new PO decision. |
| `G-LEGAL-FUTURE` Verified identity, rights, GPL/BPE compliance review | Conditional/future only. Current source/wheel/sdist excludes BPE and copied dependencies; bundle/container/installer or an action whose policy requires verified identity reopens review ([RELEASE_BLOCKERS §§0-1](RELEASE_BLOCKERS.md), lines 50-100). | Internal distribution-policy records: `d75c8db`, `b008a96`, `d493691`, `e8c00a4`; ADR-028. | **Not established now.** Repository records conditional licensing facts, not a current counsel-signature rule. | Ensures a later target obtains evidence appropriate to its actual rights and contents. | Deferable; no legal real name, counsel identity, or opinion is required or fabricated for the current target. | `PUBLIC_*`, `BUNDLE_OR_CONTAINER`, `COMMERCIAL_DISTRIBUTION`, `THIRD_PARTY_CONTRACT`, `LEGAL_ENTITY_TRANSFER`, `COPYRIGHT_REGISTRATION`. | `DEFER_TO_TRIGGER` | Yes, when a trigger occurs. |

### Roll-up ambiguity identified at audit baseline; now redefined by PO policy

At the baseline, `G-SEC` was described as an independent Security Reviewer
sign-off while the final table contained **PO, TL/release owner, QA, and Privacy
Reviewer only**; `G-RISK` was also outside that table. The audit therefore
found the "final human-signature gate" to be an ambiguous roll-up, not an
independent technical control. The subsequent explicit PO decision implements
the recommended `REDEFINE`: current records use objective evidence plus any
applicable PO authorization, and defer the unsupported role table. It does not
silently satisfy `G-SEC` or `G-RISK`—the former's technical evidence remains
required and the latter remains a PO decision.

## Role-specific conclusions

### Security Reviewer

The role first appears in the internal RC artifact package (`d668c6d`). No
repository record identifies an external authority or a PO decision requiring
an independent person for the current controlled target. Its intended assurance
is substantive, and technical evidence currently includes the canonical scanner
finite disposition, ADR-008 independent technical review, credential isolation,
network denial/fake transport, redaction, BPE fail-closed ordering, and
regression evidence. A named independent human can add judgment and separation
of duties; it is not objectively established as necessary **now** for this
one-owner posture. Retaining it is an internal policy choice.

### Privacy Reviewer

The role has the same internal RC-template origin. The current technical review
provides the intended artifact/Vault/template assurance but explicitly does not
pretend to be a human signature. A human privacy review becomes proportionately
stronger for public or customer-facing distribution, real shared-user data, or
a changed Vault/template/build boundary. For this private controlled target,
the independent-person requirement is an internal governance choice; technical
privacy controls remain non-negotiable.

### TL and QA

The project records an owner/PO but identifies no separately existing human TL
or QA in the personal-project governance model. Requiring their distinct named
signatures would therefore invite fabricated identities. Their functions are
useful: release-boundary review, test/artifact verification, and authorization
of risky operations. In the current profile, those functions should be attached
to verifiable evidence and an explicit owner decision. Separate roles make
sense after a `MULTI_DEVELOPER_TEAM`, external customer, or broader distribution
trigger.

### Product Owner

PO authority is not redundant. It is required for real side effects, release
scope, at-most-once risk acceptance, and whether qualified real Deep Analysis
output meets product intent. These are choices that objective tests cannot make.
This audit does not recommend removing `G-RISK`, `G-OPS-SMOKE`, `G-OPS-VAULT`,
or `G-PO-OUTPUT`.

### Legal/counsel

No current document establishes an external legal-reviewer signature for the
current controlled source/wheel/sdist posture. The record deliberately avoids
claiming verified identity or legal rights beyond the current pseudonymous
attribution. Legal/rightsholder evidence becomes relevant if a future trigger
changes physical contents, commercial commitments, ownership, or public scope.
This audit neither makes a legal conclusion nor removes the conditional gate.

## Technical gates versus governance gates

| Technical / operational evidence gate | Current state | Not replaceable by a signature-policy change |
| --- | --- | --- |
| TASK-016 live Provider qualification | BLOCKED: OpenAI credential-blocked; Local unqualified; Kimi adapter `1/2` / `SCHEMA_INVALID`. | Yes |
| PO acceptance of real qualified-provider Note V2/Weekly V2 before TASK-016G | BLOCKED; no eligible real output exists. | Yes — it is a PO product decision, not ceremony. |
| Real operational validation | BLOCKED / unauthorized: configured doctor, recovery, smoke, real Vault/user-note, and launchd evidence are outstanding. | Yes |
| Canonical scanner | Exit `1`, exactly 11 finite accepted fixtures; not PASS and no broader exception. | Yes |
| Privacy distribution boundary | Technical evidence approved; P2 historical controlled-source governance metadata remains for broader/public source re-review. | Yes |
| ADR-008 / ADR-028 / BPE boundary | Preserved; ADR-028 excludes the BPE asset from current artifacts. | Yes |

Human/governance gates are `G-SEC`, `G-PRIV`, `G-RISK`, the three operations
authorizations, `G-PO-OUTPUT`, `G-FINAL`, and the two recorded/conditional
distribution decisions. They should never be presented as technical defects
merely because a signature cell is empty.

## Proposed trigger-based profiles — not applied

### Current personal / private / proprietary / controlled profile

1. Preserve all fail-closed technical gates, package inspection, scanner scope,
   privacy boundary, and no-fabrication rules.
2. Require the actual owner/PO to authorize real side effects, accept the
   at-most-once risk, make distribution-scope decisions, and accept qualified
   real Deep Analysis output.
3. Treat named independent Security/Privacy, TL, QA, and final multi-role
   signatures as deferred controls unless the PO affirmatively chooses to retain
   them. Record objective technical evidence and a single owner release decision
   instead; do not manufacture substitute roles.

### Broader/public source or public package profile

Restore an independent Security and Privacy review; resolve the P2 source-hygiene
issue; define who performs release and QA functions; re-evaluate the scanner
exception and all artifact/licensing facts for the broadened target.

### Commercial third-party distribution profile

Use the broader/public profile plus a defined release owner, separation of
duties where feasible, target-specific rights/notice/compliance review,
contractual requirements if any, customer-data/privacy review, and a legal
record appropriate to the selected transaction. The profile is proposed only;
it is not an assertion that a particular law currently applies.

## Adversarial self-review

- No external requirement was classified from the word "required" alone; each
  was tested against repository evidence and marked **not established** when no
  concrete authority appeared.
- No internal requirement was called law, and no legal counsel/reviewer identity
  was invented.
- PO authority over real side effects, risk acceptance, distribution scope, and
  output acceptance is retained.
- Private posture did not erase security/privacy technical controls, the scanner
  non-zero exit, or the P2 source-hygiene re-review trigger.
- Provider qualification, operational validation, TASK-016, ADR-008, ADR-028,
  BPE disposition, TASK-014B9, TASK-014B11, and distribution scope are not
  waived or changed.
- The finite scanner exception remains exactly 11 known fixtures; it has not
  been broadened or called PASS.

## Product Owner decision package

### Answers

- **A. Externally required human gates now:** none established by repository
  evidence (`0`).
- **B. Purely project-internal gates:** all 11 inventory controls for the
  current posture.
- **C. Conservative RC-template gates:** `G-SEC`, `G-PRIV`,
  `G-OPS-RECOVERY`, and `G-FINAL`; this is a provenance classification, not an
  assertion of an unrecorded author identity.
- **D. Redundant organizational ceremony now:** the separate TL/QA role
  signatures and final four-role table lack an established role model; no gate
  is automatically removed.
- **E. Genuine PO decisions to retain:** `G-RISK`, `G-OPS-SMOKE`,
  `G-OPS-VAULT`, `G-PO-OUTPUT`, and any new distribution-scope decision.
- **F. Deferable gates:** independent Security/Privacy signatures and
  conditional legal/identity review, tied to the listed public/commercial/
  physical-distribution triggers.
- **G. Technical blockers regardless of signature policy:** qualified live
  Provider; eligible real output and PO acceptance before TASK-016G; authorized
  operational validation; scanner's exact non-PASS disposition; and the P2
  source-hygiene re-review before broader/public source distribution.

**RECOMMENDED PRODUCT OWNER DECISION:**

Adopt, for the current private/proprietary controlled source/wheel/sdist posture
only, a trigger-based human-governance profile: defer named independent Security
Reviewer, Privacy Reviewer, TL, QA, and final multi-role signature requirements
until their documented trigger occurs; replace no technical gate; retain explicit
actual-PO authority for risk acceptance, real side effects, qualified-output
acceptance, and every distribution-scope change.

**EFFECT IF ACCEPTED:**

It would reclassify only `G-SEC`, `G-PRIV`, and the organizational-role portion
of `G-FINAL` as deferred/redefined for the current posture, and redefine
`G-OPS-RECOVERY` to an actual-owner authorization. At the audit baseline it
would have required a follow-up policy update; the subsequent explicit PO
decision recorded above now supplies that policy update.

**NOT AFFECTED:**

TASK-016 Provider qualification and PO real-output acceptance; operational
authorization and validation; `G-RISK`; all package/security/privacy technical
controls; scanner exit `1` and its finite exception; P2 source hygiene; ADR-008;
ADR-028; BPE exclusion; TASK-014B9; TASK-014B11; current `NO-GO`; and the ban on
push, tag, or public release.

**RISK:**

Deferral removes an additional independent human check from a private one-owner
target. Mitigation is preserved objective evidence, fail-closed controls,
explicit PO decisions for consequential actions, and automatic re-entry to a
stricter profile when a documented trigger occurs.

## Completion record

```text
RELEASE HUMAN-GOVERNANCE AUDIT COMPLETE AT 026e9b8
HUMAN GATES CLOSED BY AUDIT: 0
HUMAN SIGNATURES FABRICATED: 0
RELEASE POLICY CHANGED BY AUDIT: NO
CURRENT RELEASE STATUS: NO-GO
EXTERNALLY REQUIRED HUMAN GATES NOW: 0 (none established by repository evidence)
INTERNAL HUMAN GATES: 11 (G-SEC, G-PRIV, G-RISK, G-OPS-RECOVERY,
  G-OPS-SMOKE, G-OPS-VAULT, G-PO-OUTPUT, G-FINAL, G-SCANNER-EXCEPTION,
  G-OWNER, G-LEGAL-FUTURE)
TECHNICAL BLOCKERS REMAINING: live Provider qualification; real qualified-output
  acceptance before TASK-016G; authorized operational validation; finite
  non-PASS scanner disposition; P2 source hygiene before broader/public source.
PUSH: NO
TAG: NO
PUBLIC RELEASE: NO
```

**Current state after the explicit PO adoption:** release policy changed `YES`;
the named independent Security/Privacy, separate TL/QA, and final multi-role
requirements are deferred for the current posture only. No human gate was
silently closed, no signature was fabricated, and all retained PO and technical
gates remain as stated in the adoption table.

## PO Addendum — 2026-11-20 (Public Beta, Apache-2.0 Source Release & Cross-Platform Dependencies)

On `2026-11-20`, the Product Owner explicitly authorized transitioning the repository from private proprietary evaluation to a cross-platform **`PUBLIC_BETA`** source release under **Apache-2.0**:

- **`G-OWNER` & License Trigger Resolved for Source Release**: Root `LICENSE` carries **Apache-2.0** (`Copyright 2026 墨竹`) and `NOTICE` attributes first-party code while preserving the unbundled third-party runtime boundary (no GPL binary/wheel bundling).
- **`G-PO-OUTPUT` Scoped to `EXPERIMENTAL` Legacy Deep Analysis**: The legacy governed Deep Analysis qualification pipeline (`TASK-016`) stays fail-closed and is surfaced as `"deep_analysis_tier": "EXPERIMENTAL"`, decoupled from blocking the core Workspace AI Hub `PUBLIC_BETA` posture.
- **`mlx-whisper` Optional Extra**: `mlx-whisper>=0.4.3,<0.5` is moved to `[project.optional-dependencies].mac-whisper` in `pyproject.toml` and `uv.lock` for non-macOS / non-Apple-Silicon portability.
- **`PUBLIC_BETA` Runtime Posture**: `GET /api/v1/system` now reports `"release_posture": "PUBLIC_BETA"` alongside `"deep_analysis_tier": "EXPERIMENTAL"`.
