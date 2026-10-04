# V1X Phase 9 DR-001: exact offline acoustic qualification

Status: accepted engineering evaluation; model qualification FAILED.
Date: 2026-10-04.
Baseline: `5324ebb3c38e941168bd9de156550bbbb65573ff`, schema 32.
Authority: owner's continuous Phase 9 goal, sole engineering executor.

## Decision and result

Evaluate only `mlx-community/whisper-large-v3-turbo`, revision
`a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb`, with the accepted installed
mlx-whisper 0.4.3 and MLX 0.32.0. No alternative repository, quantization,
runtime upgrade, cloud service or downloaded speech dataset is authorized.
Existing Hugging Face download machinery fetched only config.json and
weights.safetensors. Downloaded content was treated as data; no remote code ran.

The exact candidate is **ACOUSTIC_QUALIFICATION_FAILED**. English WER 4.00%,
Mandarin CER 1.18% and mixed error 3.28% pass their clean gates. The medium
122.86-second recording fails: the real SDK returns nonfinite metadata and an
invented repetitive tail, including zero-duration and out-of-duration segments.
Strict serialization and timed validation correctly reject it. A separate
instrumented run with the same profile exposes diagnostic WER 42.39%, 22
nonfinite fields, 11 zero-duration segments and 16 duration violations, ending
at 133.08 seconds. These failures are retained, without post-hoc exclusions,
tail trimming, per-sample tuning or lowered thresholds.

The model remains installed as machine capability. Ordinary new transcription
requires a current PASSED receipt and is blocked for this candidate. Existing
trusted transcripts, Summary and timed Evidence remain usable.

## Identity and profile

The complete [model manifest](../validation/phase9/model-manifest.json) records
1,613,977,880 bytes and both regular downloaded files. The Phase 8 full
config-plus-weight identity is
`sha256:627ea4bff5510683c5919ac35d290ec3cfca957ef74a301ca46e24ec71d34751`;
manifest digest is
`bc204b003b65c104fb1ae5301c4be03575841b5ee792e232bdfae60e60d27034`.

The receipt binds the executor contract `offline-timed-transcription-v1`, both
runtime versions, exact repository/revision/digests, platform and hardware,
Python version, preprocessing tool digests, transcript contract, timestamp
policy, qualification policy and relevant implementation hashes. The measured
machine is an Apple M1 Pro, 16 GiB RAM, macOS 26.3.1 arm64, Python 3.12.11.

One frozen profile `mlx-source-auto-t0-v1` uses task=transcribe, automatic
language, temperature=0, compression_ratio_threshold=2.4,
logprob_threshold=-1, no_speech_threshold=0.6, initial_prompt=None,
word_timestamps=False, condition_on_previous_text=True, fp16=True,
beam_size=None and best_of=None. No expected words enter the decoder. The
complete tuple is in the [sealed audit](../validation/phase9/acoustic-evidence.json).

## Corpus and scoring

No suitable repository-owned multilingual acoustic corpus was available.
Installed macOS Samantha/Tingting voices generated nonpersonal known speech
offline at rate 145. ffmpeg generated mono 16 kHz PCM WAV, one small black video
with an AAC audio track, designed gaps and seeded 25 dB mild noise. Seven
required audio shapes cover English, Mandarin, alternating Chinese-English,
3.38-second speech, normal 22–25-second speech, 122.86-second medium speech,
designed silence and mild noise. Video and a repeated English run supplement
the suite. Assets are bounded and machine-local; only scripts, manifests,
ground truth and small output records enter Git.

The [specification](../validation/phase9/corpus-spec.json) and waveform/text
hashes were frozen before ASR. Changing expected text or bytes requires a new
corpus identity and new evidence. The actual corpus identity is
`3983d004bde935ebfae9de31f0954682e483a57955cc84644a04542ce12f814c`.
OS voice synthesis across OS versions is not promised byte-identical; hashes
identify the actual tested media. Synthetic voices and alternating voice
code-switching do not establish spontaneous human speech, accent, population
or public-distribution accuracy. These are private-stage gates, not Gate B or
a scientific Whisper benchmark.

Scoring alone uses Unicode NFKC and casefold. English WER uses Unicode word
tokens with apostrophes; Mandarin CER uses letter/number characters without
punctuation/space. Mixed scoring uses individual Han characters plus non-Han
word tokens and separately reports Han and Latin components. No translation,
synonym substitution, number rewriting or simplified/traditional conversion
occurs. Persisted transcript authority retains the actual model text, including
its boundary spaces. The Phase 8 cue persistence defect rejecting those spaces
was fixed with a regression test; whitespace-only cues remain invalid.

Clean gates remain WER <=15%, CER <=15%, mixed combined error <=20%.
Every required sample must pass; averaging cannot hide a failed section.
A single deterministic global Levenshtein alignment assigns observed units
once, and requires >=50% exact-unit recall in every predefined meaningful
utterance. Review replaced a weaker reusable per-utterance alignment and added
a low-aggregate-WER catastrophic-omission adversary.

## Timing, coverage and operations

The accepted timed contract requires finite, nonnegative, strictly positive,
ordered nonoverlapping millisecond cues within duration plus one second.
Known speech regions come from the separately generated utterance waveforms,
energy threshold and 20 ms padding. Each requires >=80% interval coverage and
no unexplained gap >1.5 seconds. Designed silence is outside expected speech.
Nearest segment-boundary deviations are reported as coarse diagnostics, never
as word-level precision. All successful samples pass; medium output is invalid.

Operational gates prohibit crash/OOM, UI freeze, required short/normal timeout
and medium completion beyond the existing 1800-second hard timeout. Actual
preprocessing, worker wall time, RTF, peak RSS and macOS peak memory footprint
are measured separately. Cold capability time 6.143 seconds includes runtime
import, hashing and actual loading. Successful worker RTF ranges 0.172–1.115;
medium's 9.464-second failed attempt is not successful throughput. Peak worker
footprint reaches 4,479,702,848 bytes during that failure. No crash/OOM was
observed; no machine-wide zero-swap claim is made.

The real short-worker safety test shortens only the test deadline to 0.2 seconds,
terminates the owned worker, reaches FAILED/EXECUTOR_TIMEOUT, cleans temporary
files, keeps API reads responsive and succeeds on an explicit real retry under
the unchanged production deadline. Native sandbox denies all worker networking;
HF offline flags plus denied SDK fetching/socket connects remain in force.

## Machine receipt and portable authority

Reuse existing private `.local-transcription` storage outside portable DATA;
no schema migration is needed. Engineering-only sealing writes strict measured
sample evidence, a bounded audit addressed by its SHA256 and an authenticated
receipt. A private mode-0600 random seal and keyed hardware binding reject
ordinary edits and cross-machine receipt copying. Settings accepts only model
selection and exposes no receipt writer or PASS switch. This protects ordinary
configuration workflows, not an owner replacing application code/private keys.

States are NOT_TESTED, RUNNING, PASSED, FAILED and STALE. RUNNING needs a live
owned file lock; abandoned work cannot remain RUNNING forever. Missing evidence,
invalid seal, edited audit, changed revision/weights/runtime/profile/contracts,
preprocessing or material platform identity cannot inherit PASS. Availability
and eligibility are distinct. Normal production admission rechecks eligibility
before execution; engineering evaluation explicitly injects the actual MLX
executor to measure a candidate that has not yet passed.

Completed source-bound timed transcripts are portable authority. Fresh restart,
model unavailability and actual Backup/Restore preserve exact cues, source
language, Summary and same-Content durable TIMED_MEDIA Evidence. Model assets,
seal and receipt are excluded from Backup/Restore. No transcript trust depends
on future model availability or an in-memory model. English output preference
and English UI do not translate Chinese source authority.

The existing diagnostics panel shows qualification state in zh-CN/en without
new navigation. Production Deep Analysis stays NONE, independently of acoustic
qualification. There is no automatic fallback or provider dispatch.

## Consequences

Evaluation is complete with a failed candidate. Private-stage production
activation and Bilibili-provider commencement are not justified by this result.
The next bounded work should investigate the exact model/profile's medium
decode and timeline failures with an explicit decision for any materially
changed profile. Any later candidate must earn a new receipt; this task grants
no alternative model or dependency-upgrade authorization.

See [acceptance evidence](../validation/V1X-PHASE9-ACCEPTANCE.md) for measurements,
regressions, adversarial coverage, preserved failures and fresh final review.
