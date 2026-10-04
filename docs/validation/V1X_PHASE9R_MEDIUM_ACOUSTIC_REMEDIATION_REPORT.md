# V1X_PHASE9R_MEDIUM_ACOUSTIC_REMEDIATION_REPORT

**ACOUSTIC_QUALIFICATION_FAILED — MODEL_NOT_QUALIFIED.** No bounded candidate
satisfies all required gates. No decoding profile was activated. The production
change rejects nonfinite JSON throughout the raw result before trusted storage.

1. **Starting HEAD:** `0a0eef4b2c5f321f46b2c58ed2535d521af05b5d`.
2. **Worktree/branch:** `/Users/hua/Documents/yia-worktrees/v1x-acoustic-remediation`,
   `chatgpt/v1x-acoustic-remediation`. Sole executor. [Initial verification](phase9r/worktree-start.json).
3. **Final HEAD:** reviewed implementation HEAD `103c5f1`; the final documentation
   commit SHA is reported in the conversation. Documentation adds measured evidence
   without changing the qualified tuple or executable behavior.
4. **Frozen reproduction:** exact 122.8558125s fixture SHA256
   `41d878e52cc55e7849931dcd25249a56731da0fb6b9750c65e2308ef8922d44f`.
   Unchanged worker/profile/model: strict JSON failure in 10.294s, 22 NaN
   `avg_logprob` fields, 11 zero-duration cues, 16 cues beyond duration+1s
   (22 beyond exact duration), max end 133.08s, WER 78/184 = 42.3913%.
   [Worker reproduction](phase9r/baseline-worker-product-command.json),
   [raw analysis](phase9r/baseline-sdk-analysis.json). The initial direct-file
   invocation hit a Python logging import collision; its local logs are retained.
   Reproduction uses the actual product module command, with no configuration edit.
5. **Root cause:** interaction among A/B/C/D/E, with an additional adapter gap F.
   Previous-text prompts accumulate 0/53/105/155/182/211/241 tokens. The final
   whole-input window starts at 122.08s with about 0.78s left, carries earlier text,
   and hallucinates a repeated tail. SDK timestamp construction does not constrain
   decoded token times to the available source window. Instrumentation of the
   actual timestamp filter observes 51,778 finite logits before its structural
   mask and zero afterward. Timestamp probability is computed before applying
   the mask; two consecutive timestamps forbid timestamps while the probability
   rule simultaneously forces them. Greedy `-inf - logsumexp(-inf)` creates NaN.
   That window's NaN diagnostic is copied to 22 segments. Strict serialization
   rejects the result before the Phase 8 adapter; the adapter did not originate
   the tail. Its separate permissive JSON parser accepted nonfinite metadata,
   now fixed. No evidence identifies damaged weights or a general MLX numerical
   failure. [Observed filter trace](phase9r/timestamp-filter-origin.json).
6. **Fixed matrix:** frozen before candidate output in the [plan](V1X-PHASE9R-PLAN.md).
   A whole/on, B whole/off, C 25s chunks/on, D 25s chunks/off. All other Phase 9
   options unchanged; 12 speech/video samples per profile, 48 primary runs.
   Twelve extra silence/noise controls retain the same four profiles. No tuning
   by sample and no expansion of decoding hyperparameters.
7. **Whole/on A:** 7/12 primary samples pass; all five medium fixtures fail.
8. **Whole/off B:** 9/12 pass. Original medium passes at 1.6304% WER. Independent
   medium hallucinates “Thank you” from 115.1s to 145.08s in terminal silence.
   Boundary and mixed fixtures also fail the unchanged strict ordering gate.
9. **Chunk/on C:** 7/12 pass. Original medium WER 117.9348%, despite finite valid
   aggregate timing. Fixed chunking does not prevent repeated hallucinated speech.
10. **Chunk/off D:** 8/12 pass. Original medium WER 0.5435%; independent and
    boundary partition timing, pauses and mixed omissions still fail.
11. **Selected profile:** none. Selection uses authority, accuracy, omission,
    coverage, controls and performance, not minimum WER.
12. **Chunk policy:** research only; contiguous 400,000-frame chunks at 16kHz
    (25s), shorter final chunk. Exact spans recorded per run. All PCM frames
    retained exactly once; no content-conditioned boundaries.
13. **Overlap/merge:** zero overlap. No deduplication, trimming, text repair,
    cross-chunk prompts or LLM reconciliation. Validate each chunk, reject any
    cue exceeding its source partition, add `start_frame/16000` to both times,
    then validate the complete merged result. Tests prove exact byte partition,
    offsets, retained repetition and complete-attempt failure/retry. No chunked
    product integration was shipped because the policy fails acoustic gates.
14. **Nonfinite handling:** reject NaN, ±inf and exponent overflow (`1e999`) at
    every JSON nesting level. No replacement with zero/null or metadata omission.
    All 22 baseline values are diagnostic `avg_logprob`; their window is also
    acoustically/timestamp-invalid, so sanitization would conceal failure.
    Raw nonstandard SDK JSON is retained only as explicitly NONAUTHORITATIVE
    local diagnostic files, with [digests](phase9r/retained-raw-digests.json).
    [Red regression](phase9r/checks/nonfinite-red.txt) and
    [typed persistence adversaries](phase9r/persistence-adversaries.json).
15. **Repeated tail:** invalid progression, zero durations and duration overruns
    reject complete results. Legitimate repeated phrases are retained exactly.
    Finite well-timed hallucinations cannot be distinguished safely from real
    repetition by text alone; C demonstrates this limitation. No text-deleting
    heuristic was introduced. Failed qualification prevents these candidate
    outputs from becoming product authority.
16. **Medium corpus:** original 122.8558s; independent weather lesson 121.7974s;
    continuous boundary speech 124.6001s; seven-second designed pauses 127.5484s;
    mixed Mandarin/English 122.3266s. Nonpersonal installed OS voices only.
    References frozen before transcription. Independent generation initially
    produced 114.7974s; seven seconds of terminal silence were declared and added
    before candidate decoding, and the generation-stage assets are retained.
    [Independent manifest](phase9r/independent-corpus-manifest.json).
17. **Original medium:** A 42.39% FAIL; B 1.63% PASS; C 117.93% FAIL;
    D 0.54% PASS. A/B one invocation; C/D five; one disk model load each.
18. **Independent results:** [complete measured matrix](phase9r/matrix-results.json)
    and [timeline diagnostics](phase9r/matrix-timeline-diagnostics.json).

| Medium fixture | A error | B error | C error | D error | Overall result |
| --- | ---: | ---: | ---: | ---: | --- |
| Independent | 45.06% | 0.86% | 0.00% | 0.00% | All fail authority |
| Boundary crossing | 45.65% | 0.60% | 1.80% | 1.80% | All fail authority |
| Intentional pauses | 130.43% | 0.00% | 8.70% | 1.45% | Only B passes |
| Mixed medium | 89.84% | 3.28% | 56.72% | 56.72% | All fail timing or omission/coverage |

19. **English:** clean WER 4.00% for all four profiles, within unchanged 15% gate.
20. **Chinese:** clean CER 1.1765% for all, within unchanged 15% gate.
21. **Mixed:** clean normalized error 3.2787% for all, within unchanged 20% gate.
    C/D mixed-medium omit Mandarin after chunk one; minimum utterance recall 0.
    Clean success does not offset medium failure.
22. **Timestamp/coverage:** source offsets pass deterministic tests; all actual
    boundary candidates fail authority. D independent has a 25.2s end in a 25s
    chunk; boundary has 25.04s; pauses has 29s. B boundary/mixed additionally show
    one-ULP raw float adjacency (`29.06 < 29.060000000000002`); the original strict
    gate remains unchanged. Removing that false rejection would still leave B's
    independent hallucination and negative controls unsafe. A/C/D omit speech or
    emit hallucinations on other cases; no corpus failure was discarded.
23. **Performance:** original failing medium, measured without the diagnostic
    contention. Child wall includes import/cold load, in-process time includes
    model load and decode; total includes preprocessing/harness overhead.

| Profile | Preprocess s | In-process model s | Child wall s | Total s | RTF | Invocations / loads |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| A | 0.078 | 7.320 | 9.699 | 9.790 | 0.0789 | 1 / 1 |
| B | 0.078 | 4.700 | 7.037 | 7.124 | 0.0573 | 1 / 1 |
| C | 0.073 | 9.037 | 11.348 | 11.443 | 0.0924 | 5 / 1 |
| D | 0.078 | 8.353 | 10.589 | 10.679 | 0.0862 | 5 / 1 |

    All per-sample costs are retained. The separate greedy diagnostic overlapped
    B's independent/boundary measurements; those are marked in
    [contention evidence](phase9r/measurement-contention.json). Sequential repeats
    retain exactly the same text/source times, with 7.466s/8.006s child wall.
    Browser model availability checks were also active during controls; these
    repeats are operational observations, not isolated scientific benchmarks.
    No cost advantage overrides failing authority or multilingual behavior.
24. **Memory:** `/usr/bin/time -l` original-medium peak macOS footprints:
    A 4,494,562,880 bytes; B 2,828,949,376; C 3,113,916,416; D 2,792,396,736.
    RSS roughly 1.90GB each; footprint and RSS are separate measurements.
    All chunks reuse SDK ModelHolder; no per-chunk disk reload. No observed OOM.
25. **Real audio E2E:** actual Local import → immutable snapshot → ffmpeg → exact
    MLX → validator → trusted timed transcript → Summary/Evidence passes for
    clean/short/pauses/noise speech. The full real job rerun ends FAILED because
    medium is rejected. Explicit engineering executor injection permits evaluation
    only; ordinary production admission remains blocked.
26. **Real video E2E:** actual generated AAC/MP4 and real ffmpeg/MLX pass,
    WER 4%; trusted cues, Summary and Evidence exist. No real remediated-medium
    success is claimed. [Real qualification](phase9r/real-product-qualification.json).
27. **Restart:** fresh process reverified eight successful actual transcripts;
    failed medium remains absent. [Fresh verification](phase9r/fresh-product-verification.json).
28. **Summary/Evidence:** exact source-time cue ranges, excerpts and TIMED_MEDIA
    locators resolve after restart, model absence and restore. Production DA NONE.
29. **Backup/Restore:** fresh real-job transcripts backed up and restored without
    model or machine receipt; eight authorities remain valid. Separate historical
    authority reverification also passes. No model weights included. A successfully
    remediated medium restore is inapplicable because no such authority exists.
30. **Tuple:** adapter source hash changes
    `2b2cd67c94ad0761d58e23d6ea2a4beff49d47b183c73007a58388998cfd9f17` →
    `7dd396004c71a59ab7223f647b71b0833f08b3dcf637dc9bbb30fdf90dee3f33`.
    Tuple digest `492358150842b050cf4ad83ea8379b4558346cd7d9a8e3cd64ccd1f2e5a367a3` →
    `5309e7121832457e7607d19e438c1b8c3309c6225b0c11c8bdf50c7ed0171d81`.
    Four distinct research tuple digests bind previous-text and chunk/merge policy;
    none is qualified. [Tuple/state evidence](phase9r/qualification-state.json).
31. **Receipt:** new current-adapter receipt FAILED; production_eligible=false;
    receipt identity `c037ae0f59e26722c953936a741c25133b640824b6792db049b39e9312c8321e`.
    Historical Phase 9 receipt stays historical FAILED. No PASS rewrite.
32. **No second model:** only byte-identical local copies of the authorized revision;
    weight SHA256 `951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6`.
    No repository resolution/download called. Loader snapshot_download and sockets
    denied in actual inference workers; native sandbox denies all network.
33. **No upgrades:** all 84 installed distribution versions unchanged; dependency,
    lock and toolchain files match starting Git blobs. Runtime was copied locally,
    never installed/upgraded. mlx-whisper 0.4.3 and MLX 0.32.0 unchanged.
34. **No cloud:** actual model runs under native network denial and offline flags,
    socket/HF-download denial. No external/cloud API tools or cloud transport used.
    Browser captures have zero external page requests; production DA route NONE.
35. **Schema:** 32, 31 unchanged historical migration files/rows with accepted 029
    gap. Ten isolated databases: quick_check/integrity_check OK, foreign_key_check
    empty; repository initialization verifies migration checksums. No migration 033.
    [Database evidence](phase9r/database-final.json).
36. **Adversarial validation:** 16 new focused tests plus three real typed-result
    job/persistence adversaries; all requested cases mapped below. Frozen corpus
    rewrite guard rejects before any generation/write. Existing concurrency,
    timeout, retry, receipt tamper, Settings and source-authority suites pass.
37. **Phase 9 regression:** 49 focused tests pass, including 16 remediation tests.
    Complete required real Phase 9 sample run: eight successful samples, one medium
    rejection, verdict FAILED. Full positive requalification of a selected profile
    is not applicable; no profile survived bounded selection.
38. **Phase 8 regression:** 48 operational core + 9 runtime composition + 15 legacy
    local-transcription cases pass (core+legacy combined run 63). Complete-attempt,
    single-heavy-job, timeout cleanup, distinct retry and restart remain enforced.
39. **Phase 7 regression:** Local provider/adversarial 45 pass; expanded API+Local
    suite 73 pass. Full backend also covers remaining provider-neutral contracts.
40. **Integrated V1.x:** 116 authority/Backup/Obsidian/Delta cases plus 171
    DA/Research/History/Diff cases pass. Integrated browser eight owner flows pass.
41. **Full backend:** 3,416 passed, 1 existing optional canonical-asset skip,
    2 existing negative-fixture warnings, 586.27s. No added skip or weakened test.
42. **Frontend/browser/static:** 176 frontend tests; typecheck/build; Ruff; strict
    mypy 88 source files; compileall; diff check; DESIGN lint 0 errors/warnings.
    Four browser matrices each eight zh-CN/en × 320/768/1024/1440 flows:
    acoustic FAILED state/admission; offline failure/retry/Summary/Evidence;
    Local/mixed provider; integrated owner flows. Zero console errors/overflow/
    external page requests. Six task-owned servers shut down after checks.
43. **Protected worktrees:** all 19 other worktrees retain exact HEAD/status/diffs,
    including Phase 9/8/7/main/M13 and historical closure. All 44 tracked Phase 9
    evidence files unchanged; original corpus/model hashes unchanged.
    [Preservation](phase9r/preservation.json).
44. **Commits:** `bbab441` strict nonfinite boundary and deterministic adversaries;
    `cca2fc9` frozen matrix/generator/measurement/filter trace/FAILED seal;
    `103c5f1` typed persistence adversaries and frozen-generator guard;
    final scoped documentation/evidence commit reported in the conversation.
    No merge, push, PR, accepted-history rewrite or model-weight commit.
45. **Final acoustic verdict:** ACOUSTIC_QUALIFICATION_FAILED; MODEL_NOT_QUALIFIED.
    Simple existing start/retry UI remains truthful. Bilibili work did not start.
46. **Limitations:** synthetic OS voices only; no human population accuracy claim.
    No successful qualified-medium transcript, full positive selected-profile E2E,
    or successful remediated-medium backup/restore exists. Well-timed silence/noise
    hallucinations remain possible; all 12 negative controls emitted text, including
    “Thank you” on silence and “You” on noise. These failures are retained, not
    filtered or trusted. Original strict float adjacency remains conservative.
47. **Next controlled experiment:** separately authorize deterministic local
    silence-aware segmentation using existing ffmpeg tooling, with fixed boundary
    rules, source-window timing constraints and mixed-language omission controls.
    Investigate the observed all-masked SDK timestamp conflict without replacing
    the model or upgrading dependencies. Freeze a new bounded policy and complete
    qualification before any activation. No such experiment is started here.

The [three self-review passes](phase9r/review.json) cover root cause, qualification
and product. The generator overwrite finding was fixed and manually verified.
No unresolved material implementation finding permits activation. Remaining
acoustic limitations are explicit qualification failures.

| Required adversaries | Evidence/outcome |
| --- | --- |
| 1 | Frozen exact worker and observed raw/filter trace reproduce failure |
| 2–4 | Strict nonfinite JSON, invalid temporal tail unit tests; real typed-result persistence rejection; ordinary qualification admission blocked |
| 5–9 | Frozen four-profile plan, 48 measured runs; unchanged options/references; no per-sample tuning |
| 10–13 | Exact contiguous PCM and source-offset/repetition tests; actual boundary failures retained; overlap zero, no deduplication |
| 14–16 | Complete-attempt failure and restart-from-zero tests; three job retry adversaries; one disk load across 5–6 invocations |
| 17 | B/D genuinely pass original subset, A/C fail; subset success never qualifies |
| 18–21 | Independent/boundary/pauses/mixed medium measured; failing authority/omission remains FAIL |
| 22–25 | Short passes; clean English 4%, Chinese 1.18%, mixed 3.28% all unchanged gates |
| 26 | Per-utterance global alignment detects zero Mandarin recall for C/D medium; no omission hidden |
| 27–31 | Native offline worker, actual successful short/normal audio/video; fresh restart and no-model Summary/Evidence restore; successful remediated medium cases unavailable |
| 32–34 | Changed adapter/research tuples, historical FAILED preservation, sealed FAILED receipt and Settings no-PASS regression |
| 35–40 | Exact unchanged model files, no download/upgrade/cloud, schema 32, DA NONE, 19 protected trees preserved |

V1X_PHASE9R_MEDIUM_ACOUSTIC_REMEDIATION_COMPLETE_MODEL_STILL_NOT_QUALIFIED
