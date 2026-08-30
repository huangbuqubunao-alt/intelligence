# ADR-022: TASK-014B9 replacement public-sample one-shot

## Status

Accepted — Product Owner / Tech Lead authorization, 2026-08-30.

## Context

TASK-014B9 preserves two consumed one-shot executions for historical sample `eIho2S0ZahI`:
`bd770ef` recorded `CONTENT_UNAVAILABLE`, and the distinct `d75988a..e5642fc` package recorded
`INVALID_RESPONSE`; both had `metadata/enumerate/read=1/1/0` and fail-closed application behavior.
The final disposition found a same-sample third call unjustified and the former fixed-ID package unable to
authorize another candidate. Those records remain immutable B9 evidence.

## Decision

### D-01: Historical and current qualification samples are distinct

The historical sample is retired from current B9 qualification use only; its authorizations, results, and
evidence remain preserved. It may be retired when its bounded evidence is preserved, application behavior is
not shown defective, same-sample re-execution is not justified, and a Product Owner / Tech Lead explicitly
authorizes a replacement. Retirement is neither deletion nor a statement that the historical public resource
is globally unavailable.

### D-02: One explicit package authorizes one fixed replacement sample

A separate PO/TL authorization package may name exactly one new fixed public video ID. Before its single live
invocation, the package must record its authorization source, committed contract baseline, clean execution
baseline, fixed ID, selection basis, 30-second network-call timeout, and the directory-only scope.

The package permits exactly one semantic `smoke-public-subtitles --directory-only` invocation. It permits zero
semantic retries, zero post-start substitutions, no fallback, no sample list iteration, no rotation, no
timeout escalation, and no source fix followed by a second live call. This amendment authorizes only the
current PO/TL-approved package; every future replacement requires a new explicit PO/TL authorization and a
separately committed package.

### D-03: Selection is not qualification

The fixed replacement must be public, non-private, available without account-specific credentials, within the
public YouTube/subtitle-directory content class, deterministically identifiable, and appropriate for the
directory-only boundary. A documented inventory is preferred. If none exists, one bounded public metadata
discovery operation may identify one candidate; it may not invoke the smoke entrypoint, enumerate subtitle
directories, read subtitle bodies, download media, authenticate, or evaluate candidates sequentially. Public
metadata establishes eligibility only, never qualification success. Once selected, the ID is frozen.

### D-04: Existing safety and pass criteria are unchanged

Directory-only continues to require one metadata operation, one subtitle-directory enumeration, and zero body
reads; all B11 directory validation, restricted-key, traversal, escape-prevention, and diagnostic-secrecy
boundaries remain unchanged. The existing fail-closed result taxonomy and B9 pass criteria remain unchanged.
Any nonzero exit, incorrect operation count, directory-contract failure, leak, or external failure consumes
the new package and stops live execution.

### D-05: Evidence and review

Evidence may retain only the existing safe B9 summary fields, authorization/accounting data, safe relative
filesystem effects, cleanup result, and deterministic validation. It must not retain body content, raw
responses, URLs, titles, paths, exception text, credentials, or user data. The amendment and each execution
require independent adversarial review; neither a B9 result nor this ADR is release approval.

## Consequences

The current PO/TL message may issue one replacement-sample package only after this ADR is committed, reviewed,
and the candidate is fixed in a committed package. TASK-014B9 remains `BLOCKED / NOT QUALIFIED` until that one
package qualifies. TASK-014B11 and TASK-016 are unaffected.
