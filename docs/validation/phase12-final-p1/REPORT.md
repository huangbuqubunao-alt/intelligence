# INTELLIGENCE_PHASE12_FINAL_P1_REMEDIATION_REPORT

1. **Starting HEAD:** `bdd30cc37dcd9f956c3a9c6185ad12433c08ef8f`; exact isolated starting tree.
2. **Worktree / branch:** `/Users/hua/Documents/yia-worktrees/phase12-final-p1-remediation` / `codex/phase12-final-p1-remediation`.
3. **Protected fingerprints before:** [Full before fingerprint](protected-before.json): HEAD, index bytes, status and tracked/nonignored-untracked file bytes/modes for nine protected trees; summarized below.
4. **P1-1 reproduction:** Exact base: progressing-body regressions fail at the original deadline. Real pre-fix NASA: 2/3 success, one NETWORK_UNAVAILABLE at 10.001 s; Google Developers: 3/3 success in this small sample. [Red run](red.txt), [real pre-fix sample](alias-before.json).
5. **P1-1 root cause:** One ten-second deadline spans transport, headers and the entire up-to-4-MiB HTML body; remaining time repeatedly shrinks socket timeout.
6. **Timeout/read-budget design:** Alias only: existing ten-second transport/header deadline, separate absolute 45-second body budget, each blocking read capped by min(10 s, remaining budget), 4-MiB size bound. Atom retains 256 KiB and original ten-second total deadline. No automatic retries. [Design](READ_BUDGET.md).
7. **Slow-progressing-body result:** PASS: virtual-time alias body completes beyond ten seconds; actual verified CONNECT/TLS fixture completes twelve paced seconds of body delivery. Socket-detachment regression passes. [30 regressions](p1.txt).
8. **Stalled-body result:** PASS: virtual alias/feed stalls terminate, actual TLS body stall terminates using the read timeout; progressing trickle cannot renew the 45-second absolute budget.
9. **Oversize/truncated result:** PASS: >4 MiB alias rejects RESPONSE_TOO_LARGE; incomplete Content-Length rejects NETWORK_UNAVAILABLE and cannot return partial identity.
10. **Real NASA alias reliability sample:** Final code 6/6 success, 2.937–15.556 s; earlier post-fix sample 6/6, up to 16.981 s. Final requests separated by ten seconds, sequential alternating channels. [Final sample](alias-final.json).
11. **Real GoogleDevelopers alias reliability sample:** Final code 6/6 success, 4.274–15.874 s; earlier post-fix sample 6/6, up to 10.984 s. No old-budget failure in either post-fix sample. This is bounded current-environment evidence, not a guarantee of future internet availability.
12. **P1-2 reproduction:** Exact-base transport with native proxy absent and Fake-IP DNS: ACCESS_DENIED, zero connections, global cooldown 900.0 seconds. Original API regression returned YOUTUBE_ACCESS_DENIED. [Exact-base probe](fake-ip-before.json), [red assertions](red.txt).
13. **Fake-IP security behavior:** PASS: non-global, loopback/private, empty and mixed public/unsafe DNS results fail before connection. Fake-IP is never allowed. Shared public_addresses and pinned HTTPS transport remain byte-identical to the accepted base.
14. **Error classification after fix:** Local direct-route DNS validation failure becomes NETWORK_UNAVAILABLE / YOUTUBE_NETWORK_UNAVAILABLE. Frozen UI: “无法连接 YouTube。请检查网络或 VPN 后重试。” / “Unable to connect to YouTube. Check your network or VPN and try again.”
15. **Cooldown behavior after fix:** PASS: local DNS/route failure leaves global _RATE_UNTIL unarmed. Actual provider error classification and protection are unchanged.
16. **Retry-after-route-change result:** PASS: same API/tracker/DB retries after automatic OS route becomes usable; a different channel and the originally failed channel both establish healthy baselines. No restart/reset; failed initial alias writes no source, observations or check/baseline.
17. **Genuine provider-rate cooldown regression:** PASS: HTTP 401/403/429 still arm 900 seconds and block a different channel promptly. Proxy CONNECT refusal remains a network error.
18. **Zero-config network regression:** 57/57 PASS. Native _scproxy authority, per-request discovery, environment non-authority, fixed destination, TLS verification, redirects, credentials and SSRF preserved. [Network](network.txt).
19. **Parser regression:** 67/67 PASS. Stripped feed-level ID fix, canonical UC identity and strict entry membership unchanged. [Parser](parser.txt).
20. **Phase 12 regression:** 231/231 PASS; expected duplicate-ZIP fixture warning. [Phase 12](phase12.txt).
21. **Phase 11R.1 regression:** 192/192 PASS. Bilibili Following/public captions remain unavailable; manual import remains available, no ASR fallback. [Phase 11R.1](phase11r1.txt).
22. **Integrated V1.x:** 744/744 PASS in final rerun. [Integrated](integrated.txt); exact commands/exit codes in [checks](checks.json).
23. **Full backend:** 3804 passed, 1 skipped, 2 warnings in 786.19s (0:13:06). One full run on stable remediation; inherited canonical-tokenizer provisioning skip unchanged; expected fixture warnings. [Full backend](full-backend.txt).
24. **Frontend/typecheck/build:** 207 tests/11 files PASS; focused Following/network UX 21/21 PASS; tsc -b and production build PASS. Existing dependencies copied to isolated tree, no install or lock changes. [Tests](frontend.txt), [network UX](frontend-network.txt), [typecheck](tsc.txt), [build](build.txt).
25. **Static checks:** Ruff src/tests PASS; strict mypy PASS (97 source files); compileall src/tests PASS; git diff --check PASS. [Ruff](ruff.txt), [mypy](mypy.txt).
26. **Schema:** 34; all 33 historical migration files unchanged, no schema/dependency/config changes. [Byte invariants](unchanged-invariants.json).
27. **Real NASA baseline:** HTTP 200, `UCLA_DiR1FfKNvjuUpBHmylQ`, source created, HEALTHY / COMPLETE. Final code via actual product API, normal current Mac SYSTEM_NETWORK route. [Real acceptance](real-youtube-final.json).
28. **Real GoogleDevelopers baseline:** HTTP 200, `UC_x5XG1OV2P6uZZ5FSM9Ttw`, source created, HEALTHY / COMPLETE. No DNS/hosts/proxy/env-network changes, XML injection or security bypass.
29. **baseline_at:** NASA `2026-10-07T17:24:29.048742Z`; Google Developers `2026-10-07T17:24:38.614451Z`. Both non-null.
30. **Verified frontier:** NASA verified `2026-10-07T17:24:29.048742Z`, latest publication `2026-10-07T12:32:13.000000Z`; Google Developers verified `2026-10-07T17:24:38.614451Z`, latest publication `2026-10-07T16:00:07.000000Z`. Separate fresh-process restart preserves full source authority: [restart](real-restart-final.json).
31. **Historical Content count:** 0 for both real baselines; 15 BASELINE observations each (30 total); no RUNNING checks. DB quick/integrity checks ok, no FK violations, Backup readiness true.
32. **Remaining P0:** 0 found in scope.
33. **Remaining P1:** 0 found in scope; both independent acceptance findings remediated. Independent revalidation of this new candidate remains the next gate.
34. **Deferred P2/P3:** Accepted deferred capabilities remain: PAC/SOCKS-only and authenticated proxies, other-OS discovery and broader acquisition transport; finer parser taxonomy/provider availability follow-ups. No new in-scope P2/P3 found. Phase 13/14 and M13 untouched.
35. **Protected fingerprints after:** [Full after](protected-after.json) equals before for all nine protected trees, including frozen WIP/M13 dirt. [Equality proof](protected-equality.json). No protected-tree writes performed.
36. **Final HEAD:** Final local evidence-seal commit containing this report. Exact post-commit SHA and clean status are recorded in `/Users/hua/Documents/phase12-final-p1-evidence/final-state.json` and the final response; a commit cannot contain its own hash.
37. **Commits:** Product remediation `dc9f1969d6344f243010460f875a52798552e2a2`; separate local evidence-seal commit containing this report. No merge, push, PR or history rewrite.
38. **Final verdict:** Both bounded P1s fixed; deterministic, real socket, real product, repeated alias, regression, frontend and static gates passed. Scope/self-review complete. [Self-review](SELF_REVIEW.md).
39. **Recommended next action:** Independent revalidation of the sealed local candidate against the same two P1 acceptance criteria. Retain the freeze on main adoption and Phase 13/14.

## Protected file fingerprints (before = after)

| Worktree | SHA-256 of file bytes/modes |
|---|---|
| `/Users/hua/youtube-intel` | `95b82ba586d234196a0a2e4091b61684c7d589ebc6951f7af07a33980f60d326` |
| `/private/var/folders/yk/wdmys1pn75lcr5pnnkyjv8km0000gn/T/opencode/p12-final-acceptance` | `48ba825e88bd3e067b8c3e420404824396c06e3fae3c227194d3f88487e2657a` |
| `/Users/hua/Documents/yia-worktrees/phase12-zero-config-network` | `48ba825e88bd3e067b8c3e420404824396c06e3fae3c227194d3f88487e2657a` |
| `/Users/hua/Documents/yia-worktrees/phase12-live-fix` | `05ea0bcb2935788bca12a19ad719bc1013c9f5e1f9c06db2cdd180ead045650b` |
| `/Users/hua/Documents/yia-worktrees/phase12-live-validation` | `24cd04d877b16ffe410782a6ac5c6d4029e11c8d9d4e951a61b916b0eb26d8a4` |
| `/Users/hua/Documents/yia-worktrees/phase12-fixed-candidate-validation` | `05ea0bcb2935788bca12a19ad719bc1013c9f5e1f9c06db2cdd180ead045650b` |
| `/Users/hua/Documents/yia-worktrees/v1x-youtube-following-resume` | `24cd04d877b16ffe410782a6ac5c6d4029e11c8d9d4e951a61b916b0eb26d8a4` |
| `/Users/hua/Documents/yia-worktrees/v1x-youtube-following` | `a1259342194d8a6120e5ef90f913945f8f5471f5981c7c87daec6beba0c9de3a` |
| `/Users/hua/Documents/yia-worktrees/m13-dogfood` | `5dbfeffdd5d0cb4f57a2e71953bcbb7d36a621d36f0723febe76a314afeddcff` |

Fingerprint scope includes tracked and nonignored untracked files/symlink targets/modes, HEAD, status and index bytes. Ignored caches/runtime files are not part of the fingerprint. The work was executed only in the isolated task tree and its external evidence directory.

## Corrected failures and limits

Pre-fix regressions deliberately failed: 11 failures / 9 passes on the original implementation. The final 30-case suite adds actual TLS progression/stall and socket-detachment coverage. The initial frontend dependency-copy command used the wrong relative destination; correcting it restored the existing installed tools, and all frontend gates passed. [Setup evidence](setup-failure.txt). No tests/assertions/coverage/CI were weakened, and no dependencies upgraded. The only full-backend skip is the unchanged canonical-tokenizer asset provisioning test.

INTELLIGENCE_PHASE12_FINAL_P1_REMEDIATION_COMPLETE_READY_FOR_INDEPENDENT_REVALIDATION
