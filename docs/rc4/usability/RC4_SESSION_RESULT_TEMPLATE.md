# RC4 Individual Session Result Template

Status: `BLANK TEMPLATE — NO PARTICIPANT RESULT`.

Complete this only after a real participant session, using the corresponding
observation record as evidence. This is an analyst summary, not a replacement
for raw observations. Do not invent missing behavior or quotations.

## Session identity

- **PARTICIPANT ID:** `[P1 / P2 / P3 / P4 / P5]`
- **NON-SENSITIVE PROFILE SUMMARY:**
- **SESSION DATE:**
- **BUILD SHA:** `[exact approved UX-013 bilingual test-build SHA]`
- **TEST_LANGUAGE:** `[en / zh-CN]`
- **MODERATOR:**
- **OBSERVATION RECORD:**
- **SESSION USABLE FOR SYNTHESIS:** `[YES / PARTIAL / NO]`
- **LIMITATION OR EXCLUSION REASON:**
- **PROTOCOL VERSION / CHANGES:**
- **LOCALIZATION-SPECIFIC FINDINGS:** `[references tagged LOCALIZATION / NONE]`
- **CROSS-LANGUAGE PRODUCT FINDINGS:** `[normal product category references / NONE]`

## Headline outcome

- **REACHED FIRST USEFUL INTELLIGENCE:** `[YES / PARTIAL / NO]`
- **REACHED WITHOUT REPOSITORY/RUNTIME EXPLANATION:** `[YES / PARTIAL / NO]`
- **OVERALL CORE JOURNEY:** `[SUCCESS / ASSISTED_SUCCESS / FAILURE]`
- **CRITICAL SAFETY EVENT:** `[YES / NO]`
- **ONE-SENTENCE EVIDENCE-BASED SUMMARY:**

## Required metrics

- **TIME_TO_CORE_VALUE_UNDERSTANDING:**
- **TIME_TO_FIRST_SOURCE:**
- **SOURCE_SETUP_COMPLETED:** `[YES / NO]`
- **SOURCE_SETUP_ASSISTS_REQUIRED:**
- **CHECK_NOW_DISCOVERED:** `[YES / NO]`
- **CHECK_NOW_EXPECTATION_CORRECT:** `[YES / PARTIAL / NO]`
- **RUN_STATUS_UNDERSTOOD:** `[YES / PARTIAL / NO]`
- **RETURN_ORIENTATION:** `[YES / PARTIAL / NO]`
- **INTELLIGENCE_MENTAL_MODEL:** `[YES / PARTIAL / NO]`
- **EVIDENCE_DISCOVERED:** `[YES / NO]`
- **EVIDENCE_VERIFICATION_SUCCESS:** `[YES / NO]`
- **BLOCKED_STATE_RECOVERY:** `[YES / PARTIAL / NO]`
- **AMBIGUOUS_RETRY_EXPECTATION:** `[YES / NO]`
- **DASHBOARD_PRIORITY_ISSUE:** `[YES / NO / UNCLEAR]`
- **RESOURCE_UNKNOWN_COST_UNDERSTOOD:** `[YES / NO]`
- **MODERATOR_INTERVENTIONS:**
- **CRITICAL_FAILURES:**

Use approximate durations where appropriate. Do not replace `PARTIAL`,
`NOT_REACHED`, or `NOT_COMPLETED` with invented precision.

## Task result summary

| Task | Success (`YES / PARTIAL / NO`) | Approximate duration | Assistance count | Key observed behavior | Observation reference |
| --- | --- | --- | --- | --- | --- |
| 1. First impression |  |  |  |  |  |
| 2. Determine readiness |  |  |  |  |  |
| 3. Add first Source |  |  |  |  |  |
| 3B. Controlled validation recovery |  |  |  |  |  |
| 4. Configuration comprehension |  |  |  |  |  |
| Keyboard-only overlay |  |  |  |  |  |
| 5. Check Now |  |  |  |  |  |
| 6. Leave and return |  |  |  |  |  |
| 7. Read Intelligence |  |  |  |  |  |
| 8. Verify a claim |  |  |  |  |  |
| 9A. Actionable blocker |  |  |  |  |  |
| 9B. AMBIGUOUS |  |  |  |  |  |
| 10. Return to Dashboard |  |  |  |  |  |
| 11. Resource Usage |  |  |  |  |  |

## Round-1 MUST validation

### UX-001 — production readiness

- **VALIDATED FOR THIS PARTICIPANT:** `[YES / PARTIAL / NO]`
- **OBSERVED BEHAVIOR:**
- **PARTICIPANT QUOTE:**
- **MODERATOR INTERPRETATION:**
- **LIMITATION / CONFOUND:**

### UX-002 — accessible Source configuration

- **KEYBOARD TASK PERFORMED:** `[YES / NO]`
- **VALIDATED FOR THIS PARTICIPANT:** `[YES / PARTIAL / NO / NOT_OBSERVED]`
- **OBSERVED BEHAVIOR:**
- **PARTICIPANT QUOTE:**
- **MODERATOR INTERPRETATION:**
- **LIMITATION / CONFOUND:**

### UX-006 — Source Run orientation

- **VALIDATED FOR THIS PARTICIPANT:** `[YES / PARTIAL / NO]`
- **OBSERVED BEHAVIOR:**
- **PARTICIPANT QUOTE:**
- **MODERATOR INTERPRETATION:**
- **LIMITATION / CONFOUND:**

### UX-011 — safe recovery

- **VALIDATED FOR THIS PARTICIPANT:** `[YES / PARTIAL / NO]`
- **OBSERVED BEHAVIOR:**
- **PARTICIPANT QUOTE:**
- **MODERATOR INTERPRETATION:**
- **AMBIGUOUS RETRY EXPECTED:** `[YES / NO]`
- **LIMITATION / CONFOUND:**

## Strongest positive evidence

For each item, link behavior or a real quotation. Do not list general
satisfaction without task evidence.

1.
2.
3.

## Strongest friction evidence

For each item, separate evidence from interpretation.

### Friction 1

- **OBSERVED BEHAVIOR:**
- **PARTICIPANT QUOTE:**
- **MODERATOR INTERPRETATION:**
- **PRODUCT HYPOTHESIS:**
- **TASK IMPACT:**
- **RECOVERED WITHOUT HELP:** `[YES / NO]`

### Friction 2

- **OBSERVED BEHAVIOR:**
- **PARTICIPANT QUOTE:**
- **MODERATOR INTERPRETATION:**
- **PRODUCT HYPOTHESIS:**
- **TASK IMPACT:**
- **RECOVERED WITHOUT HELP:** `[YES / NO]`

### Friction 3

- **OBSERVED BEHAVIOR:**
- **PARTICIPANT QUOTE:**
- **MODERATOR INTERPRETATION:**
- **PRODUCT HYPOTHESIS:**
- **TASK IMPACT:**
- **RECOVERED WITHOUT HELP:** `[YES / NO]`

## SHOULD-item evidence from this participant

This section records signals only. It does not decide scope after one session.

| Item | Supporting observed behavior | Disconfirming observed behavior | Task failure (`YES / NO`) | Recovered without help (`YES / NO`) | Signal (`PROMOTE / DEFER / UNCLEAR`) |
| --- | --- | --- | --- | --- | --- |
| UX-003 Source onboarding |  |  |  |  |  |
| UX-004 Dashboard priority |  |  |  |  |  |
| UX-005 Source validation |  |  |  |  |  |
| UX-012 Resource Usage / unknown cost |  |  |  |  |  |

## Severity candidates

Severity remains provisional until all five real sessions are compared.

| Issue | Related task | Evidence | Task failure count in this session | Recovery without help (`YES / NO`) | Candidate severity (`P0 / P1 / P2 / P3`) | Related backlog |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## Safety and environment accounting

- **DATA-LOSS RISK OBSERVED:** `[YES / NO]`
- **CREDENTIAL EXPOSURE OBSERVED:** `[YES / NO]`
- **TRUST BYPASS OBSERVED:** `[YES / NO]`
- **ILLEGAL AMBIGUOUS RETRY OBSERVED:** `[YES / NO]`
- **DANGEROUS SPENDING BEHAVIOR OBSERVED:** `[YES / NO]`
- **REAL NORMAL-PRODUCTION RUN USED:** `[YES / NO]`
- **REAL PROVIDER CALL COUNT:**
- **PREPARED-STATE TRANSITIONS:**
- **UNEXPECTED EXTERNAL REQUESTS:**
- **STOP CONDITION ACTION, IF ANY:**

Do not include secret values, private data, raw provider payloads, or another
participant's information.

## Post-session answer themes

Summarize only after preserving actual answers in the observation record.

- **PRODUCT DESCRIPTION:**
- **TOP CONFUSIONS:**
- **SETTINGS WITHOUT CLEAR PURPOSE:**
- **TRUST CONDITIONS:**
- **RETURN PRIORITIES:**
- **INFORMATION OVERLOAD:**
- **MISSING INFORMATION:**
- **TEACHING STILL NEEDED:**
- **FEATURES THEY WOULD USE:**
- **FEATURES TO REMOVE OR HIDE:**

## Analyst closeout

- **WHAT THIS SESSION SUPPORTS:**
- **WHAT THIS SESSION DISCONFIRMS:**
- **WHAT REMAINS UNKNOWN:**
- **POSSIBLE MODERATOR OR ORDER EFFECT:**
- **FOLLOW-UP FOR SYNTHESIS, NOT FOR THIS PARTICIPANT:**
