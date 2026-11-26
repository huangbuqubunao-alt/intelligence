# V1X Phase 9 acoustic acceptance evidence

Baseline: `5324ebb3c38e941168bd9de156550bbbb65573ff`, schema 32.
Worktree: `/Users/developer/Documents/yia-worktrees/v1x-acoustic-qualification`.
Branch: `chatgpt/v1x-acoustic-qualification`.
Decision: [DR-001](../decisions/V1X-PHASE9-DR-001-acoustic-qualification.md).
Final result: **ACOUSTIC_QUALIFICATION_FAILED**; evaluation completed.

## Evidence and scope

The [immutable measured audit](phase9/acoustic-evidence.json) has SHA256
`84e53a28ec90fc68d440951eda26f338f63cd381f2dece29628d8062d784ea13`.
Its tuple, complete model/corpus manifests, actual transcript text/cues, timings,
resource measurements, language detection and retained medium diagnostic are
engineering evidence. [Artifact digests](phase9/artifact-digests.json) identify
the committed supporting files. No model weights, source audio/video, SQLite
database, private seal or qualification receipt is committed.

Only the authorized exact model was downloaded, via existing HF machinery.
Revision `a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb`; config.json 268 bytes,
SHA256 `b34fc29e4e11e0a25e812775dd67f4dd16fc2c8eb43d28ae25ff7d660ecb6379`;
weights.safetensors 1,613,977,612 bytes, SHA256
`951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6`.
The full Phase 8 model digest and config identity are in the manifest.
mlx-whisper 0.4.3, MLX 0.32.0, Python 3.12.11, macOS 26.3.1 arm64, M1 Pro,
16 GiB RAM. Dependency/runtime upgrades: zero.

Samantha/Tingting OS TTS ground truth was frozen before transcription; all
media is nonpersonal, local and bounded. No dataset download or microphone was
used. This synthetic suite qualifies a private-stage product profile only;
it cannot establish broad real human speech accuracy. Scoring normalization
and unchanged 15%/15%/20% clean gates are documented in DR-001. Stored cues
preserve the actual output; score normalization never rewrites source authority.

## Actual machine measurements

Times use monotonic elapsed wall time around the real task-owned MLX worker.
Preprocessing includes ffprobe and PCM conversion separately. RTF divides
worker time by source duration. Every worker loads the same model/profile;
the repeated observation is warm OS cache, not an in-process model pool.

| Sample | Duration s | Worker s | Preprocess s | RTF | Error | Timed result |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| English clean | 22.565 | 3.987 | 0.220 | 0.177 | WER 2/50 = 4.00% | Trusted, coverage passed |
| Mandarin clean | 24.668 | 4.371 | 0.212 | 0.177 | CER 1/85 = 1.18% | Trusted, coverage passed |
| Mixed clean | 22.489 | 4.244 | 0.205 | 0.189 | Combined 2/61 = 3.28% | Trusted, coverage passed |
| Very short | 3.377 | 3.765 | 0.208 | 1.115 | WER 0/6 = 0% | Trusted, no hang |
| Medium | 122.856 | 9.464 | 0.255 | 0.077 failed attempt | Diagnostic WER 78/184 = 42.39% | FAILED, rejected |
| Designed pauses | 22.907 | 4.079 | 0.213 | 0.178 | WER 0/37 = 0% | Trusted, silence excluded |
| Mild noise | 22.588 | 3.896 | 0.222 | 0.172 | WER 2/50 = 4.00% | Trusted, coverage passed |
| Video | 22.565 | 3.909 | 0.225 | 0.173 | WER 2/50 = 4.00% | Real extraction, trusted |
| English repeat | 22.565 | 3.915 | 0.148 | 0.173 | WER 2/50 = 4.00% | Identical score/authority |

Mixed components: Han 0/42 = 0%; Latin 2/19 = 10.53%. Detected languages are
en/zh/zh for clean English/Mandarin/mixed; mixed has one SDK language label,
not a claim of perfect per-word language labeling. Global meaningful-utterance
recall and expected-speech interval diagnostics pass on successful samples.
Coarse boundary deviations are retained in the audit; no word timing accuracy
is invented. The validator rejects medium's invalid timeline.

First real model compatibility/load operation: **6.143 s**, including runtime
import/probe and full identity hashing. `/usr/bin/time -l` measures successful
worker peak RSS about 1.852–1.867 GB. Largest observed peak RSS is 1,875,263,488
bytes and macOS peak memory footprint 4,479,702,848 bytes, in the failed medium
attempt. These distinct OS metrics are not conflated. No worker crash/OOM or
UI freeze occurred. Existing machine compressed/swap state was observed;
evidence makes no machine-wide zero-swap assertion.

Medium diagnosis retains 22 nonfinite avg_logprob fields, 11 zero-duration
segments and 16 end timestamps beyond duration plus one second. Last end is
133.08 s for 122.856 s media. The original worker fails strict JSON output
(`ValueError: Out of range float values are not JSON compliant: nan`); a second
instrumented same-profile SDK run exposes invented repetitions and
`TRANSCRIPT_INVALID`. Diagnostic WER is from that diagnostic run, not an
invented score for the original worker that never returned valid JSON.

## Real product authority and offline proof

[Product verification](phase9/product-verification.json) and
[fresh final restart](phase9/fresh-restart.json) verify eight successful
observations (English repeat shares the same immutable Content): real Local
snapshot -> ffprobe -> preprocessing -> actual downloaded MLX model -> timed
validation -> trusted persisted transcript -> fresh process -> Summary ->
same-Content durable TIMED_MEDIA Evidence. The video uses actual AAC extraction.
No deterministic fake executor participates in this acoustic path.

Every Evidence excerpt and start/end equals the selected stored real cues.
No candidate refs become final Evidence. Model selection cleared after success
preserves trusted transcript/Summary/Evidence; new transcription reports
MODEL_MISSING without fallback. Actual Backup/Restore excludes model, private
receipt and seal; restored trusted authority works with no model and NOT_TESTED
machine qualification. English output preference/UI preserves Chinese source
transcript language and text.

Workers use the existing native sandbox `(deny network*)`, deny SDK
snapshot_download and socket connects, and set HF/Transformers offline flags.
Successful real transcriptions ran with that native denial after download.
A native socket probe returns permission errno 1 even for loopback. No fetch,
cloud/provider dispatch or source upload occurs. Server test guards additionally
block non-loopback/provider sockets; browser routes reject external requests.
Qualification sealing and scoring run locally, without web/API lookup.
Two preexisting DA localhost metadata-discovery attempts in the restart harness
were denied by the provider guard before any connection or inference; the
blocked attempts are retained in blocked-provider-discovery.jsonl. The final
real browser server suppresses those probes while retaining DA route NONE.

The real short timeout adversary uses a test-only 0.2 s worker limit while
production stays 1800 s. It reaches FAILED/EXECUTOR_TIMEOUT in 1.654 s including
preprocessing, cleans temporary files, keeps API latency <=0.000343 s and
succeeds on an explicit real retry. Abandoned qualification RUNNING locks are
also reconciled. Cold/warm observations do not alter authority semantics.

## Validation gates

All committed check outputs are in [checks](phase9/checks/full-backend-acceptance.txt).

| Gate | Result |
| --- | --- |
| Starting Phase 8 baseline | 45 passed before changes |
| Final Phase 9 + focused offline contract | 81 passed |
| Phase 8 backend regression | 57 passed |
| Phase 7 backend regression | 58 passed |
| Comprehensive integrated V1.x backend | 986 passed |
| Full fresh backend acceptance | 3400 passed, 1 existing optional asset skip, 2 negative-fixture warnings, 580.71 s |
| All frontend tests | 176 passed, 7 files |
| Typecheck / production build | Passed / passed, 45 modules |
| Ruff | src, tests and all five Phase 9 Python scripts passed |
| Strict mypy | 88 source files passed |
| compileall | src, tests and Phase 9 scripts passed |
| Design lint | Both DESIGN.md references: zero errors/warnings |
| Docs and diff | Relative-link/fence checks and git diff --check passed |
| Real acoustic browser | 8 zh-CN/en × 320/768/1024/1440 flows; zero errors/external requests/overflow |
| Phase 8 browser | 8 fixture flows plus separate actual-video process restart/retry flow |
| Phase 7 browser | 8 Local provider flows |
| Integrated browser | 8 mixed V1.x flows covering Research/History/Diff/Knowledge Delta/Settings/YouTube/DA NONE/Obsidian |
| SQLite real/safety/restored/Phase 8 fixture/Phase 7 fixture after server shutdown | quick_check=ok, integrity_check=ok, foreign_key_check=[] |
| Schema/migrations | 32; 31 migration files and historical checksums unchanged; accepted ordinal 029 gap |
| Protected trees and dependencies | All 18 other worktrees unchanged; all 83 installed dependency versions and lock/toolchain files unchanged |

The optional o200k canonical asset test keeps its existing skip condition and
needs separately supplied `YOUTUBE_INTEL_O200K_TEST_ASSET`. No new skip, removed
assertion or weakened threshold was introduced. Duplicate-ZIP and malformed
Pydantic negative fixtures produce the two existing warnings.

## Required adversarial evidence map

| Owner cases | Evidence |
| --- | --- |
| 1–9 incomplete/present/tampered assets, revision/runtime/profile/contract changes, Settings cannot mint PASS | unit/test_acoustic_qualification.py and integration/test_acoustic_qualification_boundary.py; complete-file deletion, tampering, ordinary production admission and unsupported API-field tests |
| 10 frozen ground truth | Generator spec guard, corpus hashes, edited receipt expected/corpus SHA rejection |
| 11–13 deterministic English/Chinese/mixed | unit/test_acoustic_scoring.py and actual per-language audit, separate Han/Latin components |
| 14 short hang safety | Real short success, real timeout kill/cleanup/retry; bounded supervisor regression |
| 15–17 silence, omission, order/timing defects | Coverage/global alignment adversaries; timestamp validator regressions; actual medium rejection |
| 18–21 repeat, cold/warm, measured performance, no OOM | Real repeat/measurements/resource records; responsive short timeout API |
| 22–29 audio/video/restart/Summary/Evidence/model absence | Actual product and fresh restart verification; exact cues/Evidence range checks; restored no-model authority |
| 30–36 offline, no cloud/upload/other repository/upgrade/Git/backup model | Native socket denial, offline real workers, scoped provisioner, preservation manifest and actual archive exclusion |
| 37–40 localized UI, no navigation, DA unchanged | LocalTranscription state matrix and real 8-flow browser report; six nav destinations; production DA route NONE |

Receipt lifecycle tests include signed test-only PASS then changed weight/revision,
each material tuple dimension, tampered audit/signature, wrong machine, symlink,
missing required category and failed required sample. Fixture PASS exercises
invalidation logic only; the real candidate's receipt remains FAILED.

## Failures, remediation and fresh review

The [initial failed run](phase9/initial-failed-run.json) is retained. Real model
boundary spaces exposed a Phase 8 persistence mismatch; the smallest fix keeps
exact output while rejecting whitespace-only cues, with persistence/restart
regression coverage. Harness mistakes confusing Evidence IDs/records were
corrected and rerun; no decoder output or ground truth was edited. A mistaken
new API test expected a return instead of the actual ApiError contract; it was
corrected to assert rejection, followed by the full 3400-test fresh acceptance.

Self-review found reusable per-utterance scoring could miss a whole omitted
section when words repeat. A single global deterministic alignment and a
catastrophic-omission regression remediate it. Receipt tuple hashes now bind
scorer/receipt policy changes. Earlier receipt evidence remains historical;
fresh-restart.json verifies the final sealed tuple separately.

The real browser initially raced an asynchronous model reconfiguration and
then exposed missing DA/Backup service assembly in its isolated server. The
driver now waits for the actual PUT response; the server composes those existing
services with DA NONE. Error assertions remain strict. Final eight-flow run
passes unchanged functional, external-request and console assertions.

Final review inspects baseline-to-final code, tests, scope of downloaded files,
manifests, corpus ground truth, exact output, scoring, resource metrics,
timestamps/coverage, sealed qualification/invalidation, offline worker, UI and
portable Summary/Evidence authority. No in-scope unresolved implementation
defect remains. Failed model behavior is the truthful qualification result.
There was no merge, push, PR, dependency upgrade, migration or protected-tree edit.
The [fresh code review record](phase9/fresh-review.json) binds the inspected code
HEAD and final failed receipt. The subsequent scoped documentation commits add
only decision/acceptance records and measured artifacts.

Next phase: bounded investigation of this exact candidate's medium decoder and
timeline defect, with a new explicit profile decision before requalification.
Do not begin provider expansion on the basis of a failed acoustic candidate.
