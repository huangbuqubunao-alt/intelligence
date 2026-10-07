# Phase 12 zero-config YouTube network contract

Owner-authorized scope, exact base ab591a250f818059cb027314b87173e56c097e2a.
Sole executor; schema 34; no dependency, migration, settings, daemon or provider expansion.

Before: alias resolution used yt-dlp with proxy='', independent of Atom's pinned
public-address HTTPS socket. Both bypassed the user's macOS system HTTP proxy.
Feed XML identity/membership and tracking authority are already accepted.

Decision: one narrow YouTube-owned transport, fixed www.youtube.com:443, HTTPS.
Re-read current macOS SystemConfiguration at every request using _scproxy's
_get_proxies(), the native bridge used by CPython urllib.request's explicit
getproxies_macosx_sysconf(). Never call generic getproxies(), which reads env.
No shell, executable, system-setting writes, Keychain, browser profile or credentials.
Use only the enabled HTTPS entry, which describes an HTTP CONNECT proxy for
HTTPS traffic. Strictly validate scheme/host/port and reject credentials or
malformed/unsupported configuration truthfully; do not silently bypass it.
No proxy means existing public-IP validated/pinned direct TLS. Ordinary OS VPN/TUN
routing naturally applies to these sockets. Fake-IP is never globally made public.
A proxy tunnel sends the fixed provider hostname without local destination DNS;
TLS still verifies that hostname using the default trust context. The OS proxy
endpoint is routing configuration, never content authority.

Public channel-page canonical/og:url/identifier metadata replaces Following's
unrestricted yt-dlp alias network path. Parse only bounded HTML metadata; require
one exact canonical UC identity, reject contradictory identities. No JavaScript,
secondary URLs, cookies, netrc, config inheritance or media acquisition. Existing
manual-video yt-dlp acquisition is outside this change. Atom parsing remains intact.
Requests have socket/read deadlines and response bounds (4 MiB HTML, 256 KiB Atom),
no retries and no redirects (including same-host redirects). HTTP provider refusal
remains distinct from transport/config/TLS failures. Proxy authentication is
unsupported: reject embedded credentials; a 407 fails NETWORK_UNAVAILABLE.
Read current route per hop/request, no cache/polling/persistence. Retry after a
network change needs neither restart nor reset. Existing baseline/frontier/run
and successful/provider-refusal cooldown semantics remain the authority. Only
YouTube NETWORK_UNAVAILABLE settles with a five-second retry delay, so changing
network does not impose a fifteen-minute wait. No automatic retry loop is added.

Reuse DIRECT: CPython _scproxy/SystemConfiguration, http.client HTTPS CONNECT,
ssl default verification, HTMLParser, existing public_addresses/_PinnedHTTPS.
REJECT: generic env proxy discovery, generic proxy fetch, new network dependency,
PAC execution, browser credentials, VPN brand detection. PAC-only/SOCKS-only
configuration is outside V1's explicit HTTP/HTTPS proxy contract; no PAC fetch.

Evidence: bounded pre-implementation NASA architecture probe, HTTP 200, 1,804,414
bytes, canonical link and og:url both UCLA_DiR1FfKNvjuUpBHmylQ, itemprop identifier
matching. This is architecture evidence, not a real product baseline claim.

Validation: ephemeral loopback CONNECT + test CA for approved hostname, real TLS
handshake and rejection, route transitions, provider/authority tests, zh/en retry
and 320px/desktop browser checks, regressions, bounded real product API acceptance.
