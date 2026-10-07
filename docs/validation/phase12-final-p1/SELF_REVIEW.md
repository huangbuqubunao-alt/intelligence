# Phase 12 final P1 sole-executor review

Base: `bdd30cc37dcd9f956c3a9c6185ad12433c08ef8f`.
Scope: only alias body budget and direct-route error semantics. One production
file changes. No delegation, network architecture redesign or subsequent phase.
Reuse DIRECT: existing Python standard-library HTTPS/TLS, pinned direct transport,
SystemConfiguration discovery, shared public-address validator and tracking/API.
No new library, dependency, lockfile, toolchain or generated client.

- Timeout fixed through an explicit alias-only body budget; no blind retry.
  Transport/header timeout remains 10 seconds, body deadline 45 seconds, each
  blocking body read at most 10 seconds/remaining budget, HTML at most 4 MiB.
  Atom remains 256 KiB with its original 10-second total deadline.
- Progress is insufficient to extend the absolute body deadline. Stalled reads
  terminate as NETWORK_UNAVAILABLE. Oversize and incomplete Content-Length
  cannot return partial identity metadata.
- Review finding fixed: Connection: close detaches the socket after headers.
  Capture the request socket so alias reads still get their body timeout. Avoid
  changing a closed socket after a known-length body reaches EOF. Virtual and
  actual CONNECT/TLS tests exercise this behavior.
- TLS certificate and hostname verification remain enabled. Fixed destination
  www.youtube.com:443, redirect rejection and credential-free requests remain.
- SSRF fails closed before connecting. The shared public_addresses and pinned
  transport are byte-identical to the accepted base. Fake-IP is never whitelisted;
  mixed public/unsafe results still reject. Empty answers become route failures.
- Only DNS validation at the fixed YouTube direct-route boundary is translated
  to NETWORK_UNAVAILABLE: no provider has been contacted. It cannot arm global
  provider cooldown. Actual provider 401/403/429 still arm 900 seconds and block
  another channel. Proxy CONNECT refusal remains a network condition.
- Retry succeeds on the same API/tracker/database after automatic system route
  changes, including a different channel and the originally failed channel.
  Failed alias resolution writes no source, observations or check/baseline.
- User-facing frozen zh-CN/en network copy and input-preserving Retry are unchanged;
  existing frontend tests reject leaked low-level details.
- Parser, canonical UC identity, strict entry membership, tracking/enrollment,
  frontier/history semantics, Backup/Restore, Bilibili boundaries, all historical
  migrations and schema 34 remain unchanged. DESIGN.md remains reference material;
  this remediation introduces no UI/design change requiring new design tokens.
- Strong-reasoning sole-executor review retained. Jev advisory: complex/
  strong_reasoning, confidence .96, margin .95. No routing downgrade.

Final evidence, remaining findings and verdict are recorded in REPORT.md. Real
samples qualify this bounded current-environment run; they do not guarantee that
future internet requests cannot time out. No push, main merge or PR.
