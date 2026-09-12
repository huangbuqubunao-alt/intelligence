# TASK-022A — V1 Production Cloud Transport Amendment

Status: **PRODUCT OWNER AMENDMENT IMPLEMENTED**

## Scope

This amendment depends on TASK-018B, TASK-022B, and TASK-022C.  It adds the
only legal V1 cloud transport route for Video Distillation.  It does not
qualify, authorize, or enable a provider, and does not apply to Deep Analysis,
TASK-016G, or V2.

The finite transport set is `OFFLINE_TEST` and `CLOUD_PRODUCTION`.  The former
remains the deterministic default.  The latter is represented only by the
fixed OpenAI Responses adapter identity; no caller supplies an endpoint, a
network client, provider messages, or a full transcript.

## Authorization and disclosure boundary

Cloud is default-off.  A dispatch additionally requires an explicit `openai`
provider and non-empty model, credential availability through an injected
indirect resolver, provider availability, a valid sealed
`VerifiedDistillationInput`, and either normal `QUALIFIED + AUTHORIZED` state
or a one-input, one-call qualification scope.  The scope is exact-model and
exact-semantic-hash bound; it cannot make the provider generally eligible.
Normal Source Runs never receive an unqualified-provider bypass.

The adapter consumes only the TASK-022B sealed input and has no repository,
Evidence, transcript, Preference, or feedback authority.  Its request keeps
system contract, task/personalization, and untrusted source Evidence in
separate roles.  Credentials, request bodies, Evidence excerpts, full
transcripts, local paths, and raw preferences are not ledger data.

## Dispatch safety

Reservation, verified-input identity, budget, and transport authorization all
precede the protected adapter call.  The adapter has a fixed official endpoint
identity and passes `max_retries=0` to its wire seam.  There is no provider or
model fallback, JSON repair, semantic retry, or hidden second request.

An unconfirmed post-dispatch error remains `AMBIGUOUS`; TASK-022C m016 is the
sole durable ledger authority.  Actual provider/model and cost stay unknown
when they cannot be observed, and terminal continuation/restart/scheduler
redispatch remains forbidden.

## Boundaries unchanged

No migration is created: DB remains v016, m015/m016 remain present, and m017
is absent.  This task makes no real provider or YouTube network call and does
not use credentials.  Provider qualification, real YouTube qualification,
Deep Analysis, TASK-016G, V2, UI redesign, main, RC tag, release, or push are
not authorized by this amendment.

```text
TASK-018B -> TASK-022B -> TASK-022C -> TASK-022A ->
real YouTube + one-provider qualification
```
