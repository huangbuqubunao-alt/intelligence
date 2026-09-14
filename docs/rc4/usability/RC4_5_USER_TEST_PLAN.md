# RC4 Five-Person Moderated Usability Test Plan

## Status and authority

- Status: `PREPARATION_ONLY — NOT YET RUN`.
- Round-1 implementation anchor:
  `9d0d5425e740004f4c4c056f9a55df185bf00c00`. Before each session, record the
  exact approved UX-013 bilingual test-build SHA in the participant templates.
- Study purpose: validate the Round-1 MUST experience and collect real-user
  evidence before deciding UX-003, UX-004, UX-005, or UX-012.
- Participants: exactly five real humans. P1 is the pilot and counts toward the
  five. If an environment failure makes P1 unusable, stop and ask the Product
  Owner how to proceed rather than silently recruiting a sixth participant.
- This plan contains no participant results, simulated behavior, or invented
  quotations.

No application change, provider call, release action, or SHOULD implementation
is authorized by this document.

## Research objective

Primary question:

> Can the target RC4 user reach first useful Intelligence without understanding
> repository or runtime architecture?

Secondary questions:

1. Can the participant explain the product's purpose well enough to proceed?
2. Can they determine whether the application, Video Distillation, credential,
   budget, and Source are ready?
3. Can they add and configure a Source without excessive decision burden?
4. Can they predict what **Check Now** will do and recognize that work started?
5. Can they leave, return, and reconstruct the latest Source Run outcome?
6. Can they distinguish useful Intelligence, no important result, blocked work,
   and an unconfirmed external result?
7. Can they understand Intelligence and verify a claim through Evidence and the
   original Source?
8. Can they recover safely from actionable Needs Attention states without being
   led toward an illegal retry?
9. Does Dashboard hierarchy repeatedly hide important return-state information?
10. Do validation gaps or unknown Resource Usage cost create material errors or
    unsafe expectations?
11. Can the bounded Source Edit Configuration flow be completed by keyboard?

The study must be capable of disproving every product hypothesis. Preference
alone is not task-failure evidence.

## Participants

Recruit exactly five participants using only non-sensitive profile information.
Do not record legal names, employer names, contact details, account identifiers,
credentials, or private YouTube history in research artifacts.

All participants should be Mac-first or Mac-comfortable, comfortable using AI,
and use YouTube for learning or professional information. They need not know
Python, Node, Git, databases, or this repository. Exclude anyone who already
understands this repository or has worked on the RC4 design.

| ID | Intended perspective | Recruitment signal |
| --- | --- | --- |
| P1 | Relatively non-technical AI user; pilot | Uses AI tools but does not build software |
| P2 | Product, operations, or business user | Regularly synthesizes information for decisions |
| P3 | Technology or engineering-adjacent user | Comfortable with technical products but not this architecture |
| P4 | Heavy YouTube information consumer | Regularly follows channels for learning or work |
| P5 | Evidence/cost/control-oriented power user | Actively checks sources, usage, or automation controls |

Record `TEST_LANGUAGE: en / zh-CN` for every participant. A useful recruitment
mix is 3–4 participants using `zh-CN` and 1–2 using `en`, but this is guidance,
not a quota; use the language each real participant can evaluate comfortably
and document the actual distribution.

### Neutral screener

Ask only what is necessary:

- Are you comfortable using a Mac?
- How often do you use AI tools for information work?
- How do you use YouTube for learning or professional information?
- Do you normally verify important AI-generated claims? If so, how?
- Have you worked on, reviewed, or seen the implementation of this product?

The last answer must be **No**. Store only a short, non-identifying summary.

## Format and sequence

- Method: moderated, task-based, think-aloud usability study.
- Duration: 35–50 minutes per participant.
- Sessions: P1 pilot, then P2–P5.
- Location: controlled local Mac environment using the approved SHA.
- Moderator behavior: observe first; teach only after a task is closed and only
  when necessary to continue later tasks.
- Participant may stop at any time.

After P1, the moderator may correct neutral wording, broken fixture setup, or
timing in these documents. Do not change the product. Record any protocol change
and its reason. If a task's meaning changes materially, mark affected results as
not directly comparable rather than silently combining them.

## Environment and data controls

Prepare a fresh, isolated local research workspace for each participant. Use the
exact approved build and confirm its SHA before every session. Never expose
repository paths, internal task identifiers, terminal output, other
participants' data, private accounts, or secret values.

The operator, not the participant, configures any required provider credential
outside the participant-facing UI. Presence checks must not generate content.
Participants must never enter a real credential.

Before the product is shown, set the interface to the participant's recorded
`TEST_LANGUAGE`. Keep that language stable during core tasks. Language changes
only product-owned interface text; Source names, video titles, Intelligence,
Evidence excerpts, transcripts, and participant-entered content remain in their
original language and must not be coded as untranslated UI.

Prefer existing deterministic or prepared safe data so latency and output are
comparable. Do not modify application code, manually inject database outcomes,
or create an uncontrolled provider request. If an already-authorized real
normal-production Source Run is used, record that fact and its call count in the
session result. This preparation task itself authorizes zero provider calls.

Prepare reproducible workspaces or snapshots for these user-visible states:

- READY with one safe test Source;
- credential missing;
- budget blocked;
- provider unavailable;
- Source Run accepted/active;
- completed with Intelligence;
- completed with no important new result;
- a paired malformed and corrected safe Source URL for validation recovery;
- actionable Needs Attention;
- external result unconfirmed / AMBIGUOUS;
- Dashboard with multiple Intelligence cards, Topic change, Weekly, and both
  blocking and non-blocking Attention where appropriate;
- Resource Usage containing at least one unknown-cost record.

State transitions used only to stage research must happen between tasks at a
declared breakpoint. The moderator must not imply that a staged transition was
caused by the participant. Record every staged transition as an environment
fact, not an observed product behavior.

### Session preflight

Before admitting the participant, verify:

- build SHA matches the implementation anchor;
- participant workspace is isolated and contains no prior participant data;
- browser viewport and zoom are consistent across sessions;
- required prepared states open without console errors;
- the operator can restore the baseline between tasks;
- no secret value is visible in UI, browser tools, notes, or screen recording;
- provider call counter is zero unless a separately authorized live run is
  explicitly planned;
- observation and session-result templates are blank;
- recording consent is obtained if audio, video, or screen capture is used.

## Task protocol

Use the exact participant-facing prompts in
`RC4_MODERATOR_SCRIPT.md`. Do not name the feature under investigation before
the participant encounters it.

| # | Task | Main evidence | Backlog link |
| --- | --- | --- | --- |
| 1 | First impression | Core value and first intended action | Round-1 outcome |
| 2 | Determine readiness | Independent prerequisite comprehension | UX-001 |
| 3 | Add first Source, then correct one controlled invalid entry | Completion, hesitation, decision burden, error recovery | UX-003, UX-005 |
| 4 | Explain configuration | Required-versus-advanced mental model | UX-003, UX-005 |
| 5 | Check Now | Discoverability and expectation | UX-006 |
| 6 | Leave and return; interpret no-important-result completion | Durable run orientation and truthful terminal meaning | UX-006 |
| 7 | Read Intelligence | Output mental model and value | Round-1 outcome |
| 8 | Verify a claim | Evidence discovery and original-source verification | Trust contract |
| 9 | Needs Attention | Safe recovery and AMBIGUOUS no-retry expectation | UX-011 |
| 10 | Return to Dashboard | First fixation and hierarchy | UX-004 |
| 11 | Resource Usage | Usage discovery and unknown-cost interpretation | UX-012 |

At least two participants also complete the keyboard-only Source Edit
Configuration overlay task. Choose them before their sessions rather than in
response to performance. A separate moderator verification may supplement but
does not replace the participant evidence.

### Controlled-state allocation

Every participant sees both parts of Task 9: one actionable blocker
(credential missing or budget blocked) and AMBIGUOUS. Across the five sessions,
ensure credential, budget, and provider-unavailable readiness states are each
observed by at least two participants. All participants see READY at least once.
Record the order; rotate blocker order where practical to reduce learning bias.

## Observation method

For every task, keep four evidence layers separate:

1. **OBSERVED BEHAVIOR** — visible actions and sequence.
2. **PARTICIPANT QUOTE** — verbatim words, only when actually spoken.
3. **MODERATOR INTERPRETATION** — a cautious explanation of the behavior.
4. **PRODUCT HYPOTHESIS** — a testable proposition, not a concluded fact.

Record approximate durations. Do not imply stopwatch precision when timing is
estimated. Note every moderator assist, the prompt used, and whether the
participant recovered without help.

## Metrics and coding rules

Record these per participant:

| Metric | Recording rule |
| --- | --- |
| `TIME_TO_CORE_VALUE_UNDERSTANDING` | From first unobstructed product view until a sufficient core-value explanation; use `NOT_REACHED` if absent |
| `TIME_TO_FIRST_SOURCE` | From Task 3 prompt until saved Source confirmation; use `NOT_COMPLETED` if absent |
| `SOURCE_SETUP_COMPLETED` | `YES` only when the Source is saved without moderator execution |
| `SOURCE_SETUP_ASSISTS_REQUIRED` | Count substantive hints or actions; neutral think-aloud reminders do not count |
| `CHECK_NOW_DISCOVERED` | `YES` only if found without location guidance |
| `CHECK_NOW_EXPECTATION_CORRECT` | `YES / PARTIAL / NO`, based on expected scope and effect before click |
| `RUN_STATUS_UNDERSTOOD` | `YES / PARTIAL / NO`, based on participant explanation after start |
| `RETURN_ORIENTATION` | `YES / PARTIAL / NO`, based on finding and explaining latest run after leaving |
| `INTELLIGENCE_MENTAL_MODEL` | `YES / PARTIAL / NO`, based on treating Intelligence as synthesized product output |
| `EVIDENCE_DISCOVERED` | `YES` only when Evidence is found without naming it first |
| `EVIDENCE_VERIFICATION_SUCCESS` | `YES` only when original-source relationship is correctly explained |
| `BLOCKED_STATE_RECOVERY` | `YES / PARTIAL / NO`, based on selecting a safe relevant action |
| `AMBIGUOUS_RETRY_EXPECTATION` | `YES` if participant expects or seeks retry of the protected execution; this is undesirable |
| `DASHBOARD_PRIORITY_ISSUE` | `YES / NO / UNCLEAR`, based on observed misses, not stated preference alone |
| `RESOURCE_UNKNOWN_COST_UNDERSTOOD` | `YES` only when participant explains unknown is neither zero nor free |
| `MODERATOR_INTERVENTIONS` | Count substantive teaching, location hints, or task completion help |
| `CRITICAL_FAILURES` | Count trust/safety failures or core journey tasks that could not continue |

Task success is `YES`, `PARTIAL`, or `NO`. Define `PARTIAL` with a note; never
convert ambiguous observation into a more precise score.

## Moderation safeguards

Do not:

- describe architecture or tell the participant where to click;
- mention prior expert concerns before observation;
- ask whether a specific redesign is desired;
- bias participants toward Dashboard, configuration, progress, or usage
  complaints;
- praise or correct a path while the task is active;
- interpret silence as comprehension;
- turn a participant preference into a severity finding;
- fix the product or alter the tested build between sessions.

Use the intervention ladder in the moderator script. Close a failed task before
teaching enough context to continue.

## Safety stop conditions

Stop the active scenario immediately if there is possible:

- data loss or unintended mutation;
- credential exposure or request to enter a private credential;
- trust-authority bypass or ungrounded Intelligence presented as trusted;
- retry/redispatch of an AMBIGUOUS protected execution;
- automatic budget increase, hidden spending, or uncontrolled provider call.

Preserve non-sensitive evidence, label it `POTENTIAL_P0`, record the affected
task and participant ID, and notify the Product Owner. Do not reproduce or fix
the issue during the research session.

## Severity rubric after five real sessions

| Severity | Evidence threshold |
| --- | --- |
| P0 | Unsafe, trust-breaking, or core journey impossible for broadly relevant participants; a single credible safety event may qualify |
| P1 | Repeated major task failure or severe misunderstanding across relevant participants |
| P2 | Meaningful repeated friction or confusion, but participants can continue safely |
| P3 | Isolated polish issue or preference without meaningful task impact |

For every candidate record `PARTICIPANTS_AFFECTED` (`0–5`), task-failure count,
and `RECOVERY_WITHOUT_HELP` (`YES / NO`). Do not promote an issue merely because
one participant dislikes it.

## SHOULD decision rules

- **UX-003:** promote toward final RC4 only if multiple participants materially
  struggle to add their first Source, treat every field as required, or
  misunderstand required versus advanced choices.
- **UX-004:** promote only if blocking Attention or important return-state
  information is repeatedly missed because of Dashboard hierarchy.
- **UX-005:** promote only if entry/configuration errors repeatedly fail to help
  participants identify and correct the affected field.
- **UX-012:** promote only if Resource Usage or unknown cost creates repeated
  incorrect spending expectations or prevents meaningful control.

Reporting format **EXAMPLE ONLY:** `3/5 participants`. Do not generalize a count
into a population percentage. An isolated preference may be deferred even if
strongly worded.

## Completion gate

Preparation is complete when the five required documents exist, contain no
results, and pass documentation-only scope checks. Research is complete only
after exactly five real session observation and result records are filled,
safety events are resolved or escalated, and the synthesis is reviewed by the
Product Owner.

The next action after preparation is recruitment and real moderated sessions,
not product implementation.
