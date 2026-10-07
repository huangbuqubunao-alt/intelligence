# Alias-only read policy

The accepted transport used a single deadline from request start through EOF.
Real alias HTML is about 1.6–1.8 MiB; a body that continued making progress was
therefore rejected at ten seconds. The pre-fix real sample observed NASA fail at
10.001 seconds. Virtual-time regressions reproduce mid-body failure on the exact
base, and an actual loopback CONNECT/TLS response now finishes after twelve
seconds of paced delivery without retries.

The bounded remediation keeps the existing transport/connect/TLS/header limits.
A successful alias response must receive its headers before the original
10-second deadline. Only then does its separate absolute 45-second body budget
start. Every blocking read gets min(10 seconds, remaining body budget). The
existing 4-MiB byte bound, identity encoding requirement, truncation rejection
and redirect rejection remain. A progressing body cannot renew its total budget.
The 45-second budget allows the full bound at about 93 KiB/s and gives ordinary
1.6–1.8-MiB alias HTML room without enlarging feed or global timeouts.

The response may own the socket after HTTP Connection: close. Keeping the socket
reference allows the alias policy to apply there too; once a known-length body
is consumed, its already-closed socket is not retimed. Atom remains 256 KiB and
its original ten-second total budget. No automatic request retry is introduced.

DNS validation failure in the fixed-host direct branch occurs before contact
with YouTube. It still prevents connection, but is projected as local route
NETWORK_UNAVAILABLE instead of provider ACCESS_DENIED. Empty DNS answers are
also unusable. The shared validator and pinning/TLS code are unchanged. Actual
provider 401/403/429 handling and 900-second protection are unchanged.
