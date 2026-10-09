# Intelligence Dogfood D2-02 validation

Base: `c990e698c9e0c5f3ea65e62c8ecfde09db60556b`.
Implementation: `f5d2132`, fixes `900ef8b`, regression adapter `c2a74e3`, native-only saved-result recovery `eedd9c6`.
Design and reuse decisions: [DESIGN.md](DESIGN.md).
Handoff / independent review: [handoff](../../../handoffs/DOGFOOD-DAY2-D2-02.md).

## Actual native 2 GiB proof

[actual-native-media.json](actual-native-media.json) and
[raw completion](actual-native-media-final.txt): real AppKit selection, exact
2,147,483,648 bytes, authorized descriptor → APFS clone → bounded SHA/probe →
atomic independent snapshot → ordinary Content read. Confirm accepted in 0.0021s;
verified Content saved in 6.65s under concurrent test load. Clone syscall 0.00036s;
verification remains necessary and is not represented as instantaneous completion.
No HTTP file bytes; control requests contain only `{}` (2 bytes).

The same snapshot survives original edits, move and deletion. It passes ZIP64
backup/download/staging/activation and identical Content/Evidence/hash restoration.
Peak process RSS across the complete native+backup+restore harness: 67,633,152 bytes
(64.5 MiB); largest measured Python allocation delta 4,230,885 bytes (4.04 MiB).
No model called; timed Evidence is an isolated deterministic fixture.

Actual 2 GiB−1 native clone also completed. Actual 2 GiB stream fallback completed
(3.8s) with clone support disabled through an explicitly labelled test seam; not
an actual external non-APFS disk. First selection is real native UI; later dedupe,
near-boundary and fallback selections explicitly substitute the picker in tests.
Media fixtures are real ffmpeg one-second MP4s with a valid sparse `free` atom.
Full source bytes are hashed/copied/backed up/restored, not mocked byte counts.
A dense two-hour 2 GiB recording / actual offline ASR was not tested.

[browser-native-import.json](browser-native-import.json) proves real Chrome →
actual AppKit picker → confirmation → verification → automatic #Content navigation,
selection retained on focus, APFS method, and no `/local/imports` file-body request.
Screenshots: native-selected-two-gib.png, native-verifying-two-gib.png,
native-saved-two-gib.png. Browser fixture intentionally adds a one-second media
probe delay; its final 13.179s observation includes UI polling and duplicate verification.
Native control requests recorded in native-browser-requests.json. The clean final-source run is native-browser-reviewed-final.txt (exit zero),
with fresh isolated DATA and no page errors. Older native-browser-final.txt retains
interrupted concurrent-runner output from an earlier shared log filename.

## Compatibility evidence

[actual-large-media.json](actual-large-media.json) / actual-large-media-final.txt
prove actual HTTP streaming of 2 GiB−1 and 2 GiB plus ZIP64 restore and hash identity.
These are compatibility adapter tests, not proof of native zero upload. Primary
macOS UI has no HTTP-file fallback; the legacy endpoint remains compatible.
Browser-large-import.json proves prior HTTP adapter small/65 MiB/2 GiB/TXT and
English/Chinese/D2-01 chooser/navigation/reload regressions. Original native and
HTTP attempts and failing-development logs are retained rather than hidden.

## Reviewed faults and boundary coverage

New tests cover exact/inclusive/oversized/zero/text2MiB/supported and mismatched
formats, independent duration rejection, audio, duplicate/concurrent requests,
cancelled/expired/replayed grants, Origin/Host/fetch-header guards, path/ancestor
symlinks, source mutation, atomic publication/inode substitution, failure cleanup,
startup crash cleanup/live-stage locks, idle/total timeouts, disk shortage,
backup archive/manifest/ZIP metadata/expanded/member/file-count bounds and legacy
Schema34/35 →36 restore. Time/disk/above-limit extremes use bounded simulation;
not two hours of wall-clock waiting or a deliberately exhausted physical disk.

Reviewer identified and root fixed two P1s: actual SQLite pages must count in
backup admission; failures after committed admission must retain verified saved
Content and separately report transcript/summary/status processing failure. The
new fault tests preserve Content/Evidence and deduplicate a retry. Reviewer
APPROVE combined base...c2a74e3, independently 60 native/import checks and 73
D2-02 checks, clean whitespace diff, no remaining P0/P1 found.

Final-source test commands include `PYTHONPATH=src:. .venv/bin/python -m pytest`.
A run omitting repository root from PYTHONPATH failed four existing acoustic
script imports; no tests/scripts/thresholds were weakened. The corrected command
is rerun. One pre-existing canonical-o200k asset provisioning skip is retained.
Final engineering results are recorded below after the running gates complete.

Already completed final gates: 1978 unit/smoke tests passed, one existing asset
skip, two existing warning fixtures; 282 frontend tests passed; TypeScript and
production build passed (49 modules); strict mypy passed all 100 source files;
Ruff and git diff --check passed; D2-02 focused 75 passed; post-review integrity/
backup/adversarial 105 passed; provider/launcher/offline regressions 159 passed.
Owner checks and private recovery copy are outside the repository evidence:
`.var/d2-02/owner-*-integrity.json`, final operational report under `.var/d2-02`.
All stress tests use isolated data. Owner data are only read for integrity and
receive the expressly approved non-destructive Schema36 migration at deployment.

The full integration run caught one retained legacy transaction assertion: native
saved-file recovery initially suppressed RuntimeError before READY. eedd9c6 confines
this recovery to import_selected only; legacy adapters preserve their interruption
semantics. The original assertion remains untouched. New native interruption/retry
checks prove IMPORTED, zero partial Evidence, and exactly one Content before the
authorized retry publishes READY. Transaction/native/large regressions:102 passed.
Final complete collection:3979 tests, including20 existing security scanner tests.
All89 integration/e2e modules are rerun in four disjoint partitions recorded in
integration-final-partitions.json; no module omitted, test skipped or script changed.
Unit/smoke/security tests are rerun against the same final source.

## Final engineering acceptance (eedd9c6)

Full backend: **3978 passed, 1 pre-existing canonical-o200k asset skip** from
3979 collected. Unit/smoke/security:1998 passed, 1 skipped, 2 existing warnings
(backend-unit-security-final.txt). Integration/e2e:507 +373 +637 +463 =1980 passed,
four disjoint complete partitions, exit codes all zero. No test or gate weakened.
Frontend:282 passed across19 files. TypeScript, production build, strict mypy
(100 source files), Ruff and git diff --check all pass.

Final independent review:APPROVE base...eedd9c6, no remaining P0/P1;
62 independently executed native/import/legacy-interruption checks passed.
Earlier running-gate descriptions above are chronological development evidence;
this final acceptance supersedes their pending status. The retained full integration
failure was fixed in implementation, without changing its assertion.

Committed text logs normalize trailing whitespace only; assertions, failure traces,
counts, timing and warning evidence remain intact.
