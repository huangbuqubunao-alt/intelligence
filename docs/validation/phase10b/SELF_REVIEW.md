# Phase 10B review and remediation

Sole-executor review, per assignment. No independent-agent review is claimed.

## Provider architecture

Accepted Phase 7 had provider-aware Content/Following/artifacts and immutable
source snapshots, but Local owned source publication and MediaTranscript. This
change extracts those accepted contracts into SourceContentPublisher and a
provider-neutral transcript value. Bilibili performs acquisition and publishes
normal Summary, timed transcript and Evidence. Intelligence, Topic, Research and
Delta reuse the existing domain. No Bilibili-specific domain tables/classes.
Schema 32 explicitly excluded Bilibili: migration 033 extends those constraints
and caption failure states without adding tables, touching 029 or rewriting
historical migrations. Atomic rollback and exact histories remain tested.

Found/fixed: snapshot SQL table-name mismatch; initial staging/admission crash
could orphan Following; make Content/Following/link/snapshot/artifact admission
one transaction. Retain the accepted Local error contract after publisher
extraction. Successful caption retry clears stale Following errors. Ready
caption metadata/authority remain immutable; metadata refresh is deferred.

## Network, security and privacy

Only HTTPS BV video inputs on three exact public Bilibili hosts. Requests reach
fixed public API paths or exact subtitle CDN paths. All redirects rejected.
DNS public-address validation and pinned verified TLS close rebinding/private
network escapes. Two provider slots, two DNS workers, bounded timeout, half-second
pacing, three transient attempts and 30-second rate-denial cooldown. Denial is
terminal. Bounded streaming and compression rejection prevent large bodies and
decompression bombs. No accounts, cookie stores, credentials, proxies, CAPTCHA
workarounds, video/audio download, ASR or global search operation.

Stored metadata/captions/provenance and canonical timed authority are hash/owner
verified. Offline reread reparses exact stored raw captions and validates all
cue/text/duration rules. Evidence resolves stored artifacts, never future web
responses. Backup authority includes the same files and hashes. Corrupt caption
archives fail even after the external manifest is rehashed.

Found/fixed: bound DNS waits, reject multicast DNS, preserve provider error codes,
reject pathological Content-Length/compression, enforce caption CDN provenance,
artifact kind and acquisition timestamp/id. A mechanical current-schema edit
also changed one unrelated output-token assertion; restored it to the accepted
baseline. No assertions were removed or coverage weakened.

## Product review in actual browser

Following Add integrates the provider selector and clear one-public-video copy.
Shared Content shows uploader, publication, duration, caption language/status.
Metadata-only Content explains missing Summary/Evidence and explicit retry.
Trusted stored captions, Summary, timed Evidence, three-source Research and
ordinary Home Delta stay readable after restart/offline. Both UI languages and
320/768/1024/1440 layouts are verified with actual HTTP/SQLite browser fixtures.
Untrusted script markup renders as literal text, and no extra navigation appears.

Found/fixed: correct publication date instead of import date; suppress internal
metadata .json format from the reading UI. Initial browser assertion used the
wrong Chinese label; aligned it to established localization. A Phase 8 Research
control timeout was investigated on the rendered page/API and the stable matrix
passed. A later Bilibili click stability timeout was diagnosed with visible,
enabled controls; fresh production-build checks disable browser background
throttling and capture full failure evidence, retaining normal click assertions.
No product success is inferred from a failed browser run.

## Limits and deferred features

No creator monitoring, short-link resolution, multipart videos beyond p=1,
authenticated/private/member/paid material, comments/danmaku/favorites, global
search, media archive or acoustic fallback. The accepted snapshot duration
contract limits this first slice to two hours. Live public captions were absent
for the one public validation video; caption success is fixture-qualified only.
Endpoint availability/access policy can change; failures remain truthful and
stored authority remains portable. No legal entitlement or remote availability
guarantee is inferred from technical validation. Failed Phase 9/9R artifacts
remain unchanged; ASR production qualification and production DA route are NONE.
