# TASK-022C — Resource Ledger AMBIGUOUS Outcome Amendment

Status: **PRODUCT OWNER AMENDMENT**

## Purpose

TASK-022A discovered a persistence gap in the historical TASK-022 ledger.  The
m010 `distillation_resource_usage` status set already names `AMBIGUOUS`, but
its paired-actual-identity check requires every invoked row to contain both an
actual provider and actual model.  That is not truthful when a protected
provider request may have reached a provider but the application receives no
reliable response identity.

TASK-022C owns m016 only.  It reconstructs the ledger table without modifying
m010, preserving all historical rows, indexes, foreign keys, and append-only
triggers.  The finite status set remains unchanged; m016 permits absent actual
provider/model identity only for an invoked `AMBIGUOUS` row.  All other invoked
rows still require both identities, and uninvoked rows still require neither.

## Durable semantics

`AMBIGUOUS` means a protected provider invocation may have happened but its
completion cannot be confirmed.  It is a terminal historical result for normal
automation:

- no automatic retry or redispatch;
- no provider or model fallback;
- no conversion to `FAILED`, `SUCCESS`, `RETRYABLE`, or a generic unknown
  outcome;
- no mutation of an existing ledger row.

Unknown usage or cost remains unknown (`NULL`) unless a reliable observation is
available.  Zero cost is never fabricated for an ambiguous invocation.

## Boundaries

The only runtime alignment is the ledger validation needed to represent this
existing dispatch fact.  The checkpoint state machine, TASK-023B reservation
authority, TASK-024 orchestration, TASK-018B transcript authority, TASK-022B
verified input, trust admission, provider qualification, credentials, and
transport authorization remain unchanged.

This amendment creates no cloud transport, provider adapter, credential,
provider qualification result, YouTube ingestion, or network call.  Deep
Analysis remains **BLOCKED**, TASK-016G remains **UNAUTHORIZED**, and V2 is not
enabled.

## Migration and dependency order

`015_add_timed_transcript_evidence_bindings.sql` remains untouched.  m016 is
the forward-only `v015 -> v016` ledger reconstruction; m017 is not authorized.
Historical m010 is immutable and remains the source of the original ledger
contract.

```text
TASK-018B -> TASK-022B -> TASK-022C -> TASK-022A ->
real YouTube + provider qualification
```
