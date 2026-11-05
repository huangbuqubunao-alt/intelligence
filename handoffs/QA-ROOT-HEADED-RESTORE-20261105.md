# Root headed GUI and populated Restore, 2026-11-05

Scope: real macOS headed Chrome, Settings language roundtrip, unsaved synthetic credential draft clearing, Backup create/download/stage/explicit RESTORE/automatic restart/APPLIED, unchanged Content and Evidence views, Topics navigation. This is not real-model quality, Native chooser, onboarding or full-schema authority acceptance by the browser alone.

Product source base76ef3c2993c3dcd44a8d35189cd114b768451648 includes independently accepted passive admission, bounded qualification and QA Native wiring deltas. Only this QA runner/report changes in this commit; no product, frontend, schema, dependencies, credential, formal data or model-qualification changes.

## Actual failures preserved and tool corrections

- Initial Settings two language 409 failures were a real passive EX/admission conflict, separately fixed in accepted ba74446. Post-fix real language roundtrip passes; no HTTP failure was suppressed.
- `.var/gui-e2e/1793840085013-85593`: fresh backend readiness was true but rendered button had not reached its next10s poll. Runner now bounded-polls the actual enabled button within the existing timeout. It retains backend readiness and final disabled assertions; no click/POST retry or button manipulation.
- `.var/gui-e2e/1793840220340-85897`: actual downloaded ZIP921457 bytes, CRC valid, schema44/19 DATA. A separate real Chrome existing-archive probe proves this exact GET emits net::ERR_ABORTED while download.failure() is null and archive fully saved. Runner recognizes only one exact predeclared same-origin backup-download GET ERR_ABORTED. Required actual download event/failure-null/nonempty file and strict Restore checks remain. Other aborted/error requests fail.
- `.var/gui-e2e/1793840820655-86778`: Native-enabled page startup legitimately POSTs the origin-protected Native jobs read listing. Inspected real handler: no picker/confirm/model action. Added only that exact endpoint to the settings/restore request allowlist; all pick/confirm/cancel routes remain blocked.
- `.var/gui-e2e/1793840926696-86967`: actual stage succeeded, but Playwright response.json hit Chrome Network.getResponseBody inspector-cache eviction. A stage-only real-UI diagnostic confirms the exact error, no Restore confirmation. Runner now clones only the two actual in-page fetch responses for stage/confirm, leaving request/response unchanged and never resending. Status/body/restore-id/positive populated preview/pending restart/APPLIED checks retained. It reads neither headers nor request bodies/keys. Root explicitly cancelled owned unconfirmed diagnostic previews via the normal cancel API; no core DB/DATA removed or rewritten by cleanup.

## Final evidence

- `node --test scripts/verify_gui_e2e.failure.test.mjs`: PASS, including four real failed child-process cases and zero mutations. Final Node syntax and whitespace PASS. Tests/assertions were not removed or weakened.
- Actual headed result `.var/gui-e2e/1793841187342-87264/result.json`: success true, all required8 steps PASS, zero errors. Download saved and exact Chrome navigation abort correlated. Restore15aca6e4f3d74805bd4a1d383438d3a5 actually APPLIED after restart.
- Root independent `.var/final-checks/gui-all-sql-data-restore-20261105.json`: archive97fd614d11ae35ca4f981756fb7437c66112d6b4b5ec23a28595022e116f1744, CRC valid; schema44, all87 SQL tables every sorted row/hash and all19 physical DATA paths/bytes/hash exactly equal restored live state. Backup ready, Native capability true after actual restart, QA cloud execution false.
- No model call or new real fee in this scope. New K3.1/local qualification remains closed; historical legacy qualification unchanged. Only owned public fixture used; formal owner data/config/credentials untouched. Screenshots mask password inputs.

Final full backend, real Native small-file flow and genuine model qualification/normal paid GUI remain separate pending acceptance. Previous failures are not relabeled PASS or deleted.
