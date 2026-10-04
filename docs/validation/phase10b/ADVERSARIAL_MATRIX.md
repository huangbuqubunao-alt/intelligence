# Phase 10B adversarial acceptance matrix

Deterministic adapter and integration fixtures own routine validation. Browser
checks exercise the actual HTTP/SQLite product with fixture acquisition, not a
live-caption or qualified-model claim. The public live check retrieved metadata
and truthfully reported no caption. Test identifiers below are in
`tests/unit/test_bilibili_provider.py` (adapter),
`tests/integration/test_bilibili_content.py` (Content), and
`tests/integration/test_bilibili_three_provider.py` (three-provider), unless noted.

| Required case | Evidence |
| --- | --- |
| 1. BV URL normalization | adapter `test_normalization` |
| 2. Alternate legitimate URL | same test: mobile/bare host/p=1/share query |
| 3. Different URLs, same identity | Content restart/offline duplicate test |
| 4. Malformed BV | adapter `test_unsafe_input` |
| 5. Non-Bilibili URL | same unsafe-input test |
| 6. Localhost | same unsafe-input test |
| 7. Private redirect | adapter `test_redirect_chain_is_never_followed` |
| 8. Excessive redirect chain | same test: zero followed redirects, including allowed targets |
| 9. Unsupported scheme | unsafe-input and request-allowlist tests |
| 10. Metadata success | adapter success; Content/API; bounded live check |
| 11. Malformed metadata | adapter malformed metadata cases |
| 12. Oversized metadata | strict JSON limit and transport body/header limits |
| 13. Public caption success | adapter and HTTP/SQLite fixture import |
| 14. Unavailable caption | adapter, Content and both localized browser matrices |
| 15. Malformed caption | adapter `test_invalid_caption`; corrupt stored authority |
| 16. Negative timestamp | invalid-caption matrix |
| 17. Nonfinite timestamp | invalid-caption matrix/strict JSON |
| 18. End before start | invalid-caption matrix |
| 19. Beyond duration | invalid-caption matrix; one-second accepted tolerance |
| 20. Oversized caption | caption byte/cue/text bounds |
| 21. Language preserved | exact `ai-zh` and `zh-CN`, original text/timing tests |
| 22. Restart persistence | Content test; server restart browser matrix |
| 23. Offline after import | no requests on stored reads; database-offline.json |
| 24. Summary | shared extractive Summary read/API/browser key points |
| 25. Durable timed Evidence | exact trusted cues, stored canonical artifact/locators |
| 26. Cross-Content rejected | Content `test_bilibili_evidence_cannot_bind_another_content` |
| 27. YouTube regression | discovery/subtitle/transcription policy; integrated product browser |
| 28. Local regression | accepted provider/adversarial tests; eight Local browser flows |
| 29. Three-provider sealed Intelligence | three-provider sealed authoritative reader and dependency edges |
| 30. Bilibili Research | selected Content API and actual browser Research |
| 31. Three-provider scope | deterministic semantic packets, all three Evidence providers |
| 32. Knowledge Delta | ordinary content_completed category/test/browser Home |
| 33. Repeated import | one canonical Content, no future provider fetch |
| 34. Mutable metadata | changed remote title cannot rewrite stored authority; refresh deferred |
| 35. Changed caption | READY retry does not fetch or overwrite accepted caption |
| 36. Cookie-free | live public check; exact transport header assertions |
| 37. No browser-cookie read | narrow standard-library adapter; no browser, cookie APIs or subprocess |
| 38. No auth bypass | 401/403/412/private/paid/login-needed failures; no retry on denial |
| 39. No unqualified acoustic fallback | fail-on-call Local probe/jobs fixture; no audio/video artifacts |
| 40. Production DA NONE | unchanged composition/qualification records; boundary tests/database check |
| 41. Offline backup/restore | three-provider portable artifacts, Summary pointer and historical Research packet |
| 42. Corrupt backed-up caption | rewritten outer manifest still fails inner source authority validation |
| 43. Chinese UI | real browser layouts/status/copy, access-denial component test |
| 44. English UI | same product flows and truthful offline new-import rejection |
| 45. 320px overflow | zero across Bilibili/Local/Phase 8/integrated matrices |
| 46. Navigation | existing six primary buttons asserted |
| 47. Unexpected requests | browser external=[]; only explicitly requested BV/CID/subtitle data |
| 48. Concurrency | shared provider two-slot bound; API import one-slot; DNS two workers |

Additional attacks: control characters, malicious HTML/script title/caption,
userinfo/ports, loopback/link-local/private/multicast DNS, decompression rejection,
5,000-digit Content-Length, invalid UTF-8/duplicate JSON keys, DNS timeout,
three-attempt transient retry, rate-denial cooldown, source corruption and
staging failure before admission. No test depends on Bilibili network.
