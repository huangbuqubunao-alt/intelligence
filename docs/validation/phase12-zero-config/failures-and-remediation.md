# Failure evidence and remediation

No test, assertion, threshold or CI gate was removed or weakened.

- `PYTHONPATH=src /Users/hua/youtube-intel/.venv/bin/python -m pytest -q tests/unit/test_youtube_network.py`:
  expanded first run: 1 failed, 44 passed. Assertion expected
  NETWORK_UNAVAILABLE, received METADATA_FAILED at the alias/authority test.
  `youtube_channel.py:_resolve_public` fetched inside a ValueError parser handler;
  TrackingError subclasses ValueError. Moved fetch before parser handler. Final
  network/fresh acceptance both 57 passed.
- `npm --prefix frontend test -- --run src/workspace/CreatorFollowing.test.tsx`:
  old settled-status assertion expected generic offline copy; new copy is
  provider-specific. Updated the exact string assertion. Chinese Retry failed
  because no translation existed; added the translation. A first edit used a
  wrong cwd and did not apply, and a subsequent edit missed single-quoted text;
  stopped unchanged retries and corrected the exact source. Final frontend 207
  passed with bilingual input-preserving Retry and failed-baseline assertions.
- Phase 12 seven-file focused pytest suite: twice 2 failed / 229 passed, in
  `test_creator_following.py:test_withdrawing_the_caption_capability_leaves_bilibili_import_available`
  and `test_manual_public_bilibili_ingestion_still_works_with_creator_following_withdrawn`.
  Isolated two-test invocation also failed. Diagnostic showed
  `app_adapter_is_fixture: False`, `BILIBILI_ACCESS_DENIED`. The API created a
  live-network adapter instead of the tracker fixture. Wired the existing
  fixture adapter; its metadata then raised `KeyError: 'BV1UeHe6YEVM'` because
  that formerly-live test ID was absent. Seeded explicit historical synthetic
  metadata in those two tests. One initial text replacement missed the first
  function; corrected the exact block before retrying. The same assertions now
  pass: isolated 2, complete Phase 12 231, integrated 744, full backend 3,774.
  Bilibili production code remains byte-identical to the accepted base.
- `node .var/phase12/zero-config-browser/scripts/stored-offline-ui.mjs` initially
  timed out waiting for Retry after `page.reload()`. Reload discarded the open
  detail and invoked the existing focus/mount stale-check flow. Used a fresh
  fixture root and clicked eligible Retry in the existing open detail, preserving
  all baseline/offline/wrapping/retry assertions. Four scenarios passed.
- Harness setup corrections: corrected the historical discovery-adapter path
  from unit to integration; fixed a local Playwright relative import; fixed one
  draft-script syntax error and wrong cwd. These were setup failures, not product
  changes or skipped checks. All required checks ran successfully afterward.

Self-review also tightened proxy endpoint DNS (one second/two workers), CONNECT
bounds, HTTP truncation refusal, immediate failed-baseline messaging and accurate
successful-check cooldown copy. Security/read-bound tests were added, then the
final focused, static, full backend and frontend gates passed. Actual public
acceptance used production transport, not injected XML, a proxy fixture or test
CA. User VPN/DNS/hosts/proxy/environment settings were never modified.
