# Phase 8 — offline timed transcription

Authority: owner's continuous Phase 8 goal; sole engineering executor.
Baseline: `c09a6ae5077867610420e1aed80fe3c7abb10c08`, schema 32.

## Definition and reuse audit

Offline transcription means application-owned execution of an already installed,
compatible local runtime against an immutable imported snapshot and an explicitly
selected local model. No cloud, upload, paid provider, automatic installation or
model download is part of this contract. Transcription readiness is separate from
Deep Analysis qualification; production DA route stays NONE.

| Existing component | Classification | Phase 8 decision |
| --- | --- | --- |
| `local_content.MediaTranscriber` / `MediaTranscript` | ADAPT | Extend narrow timed boundary with raw executor provenance; shared validation/publication |
| `providers.whisper.WhisperExecutor`, `MlxWhisperAdapter` | ADAPT / TEST-ONLY production execution | Reuse approved SDK and policy approach; historical injected executor returns text only and cannot produce timed authority |
| `transcripts.LocalTranscriptionService` | REUSE historical continuation | Retain YouTube artifact/job continuation; no competing Local transcript repository |
| `transcription` resource/cache policy | REUSE / REFERENCE | Bounded execution identity; Local retains its accepted 64 MiB / two-hour bounds |
| `local_content.probe_media` | ADAPT | Preserve format/protocol validation; bounded streaming process replaces unbounded captured pipes |
| `source_authority`, managed source snapshots | REUSE / ADAPT | Existing immutable bytes, SHA-256, transactions, reread guards; add raw-output envelope v2 |
| `timed_transcripts`, cues, `VerifiedTimedTranscript` | REUSE | Integer milliseconds and existing verified authority |
| timed Summary candidates / extractive Summary | REUSE | Existing normal Summary and durable Evidence path |
| TIMED_MEDIA Evidence bindings | REUSE | No weakened ownership, binding or dependency rules |
| existing `jobs` and `job_attempts` | REUSE | Explicit new attempts, audited leases, existing schema; one local slot |
| Phase 7 timed transcriber fixtures | TEST-ONLY | Preserve historical v1 authority; never production discovery |
| demo workspace transcript controls | DEMO-ONLY | No production connection |
| automatic HF model-name loading | UNSAFE for this scope | Deny downloads and require verified local directory |
| arbitrary Whisper filename execution | UNSAFE | Never discover/execute it as the production executor |
| whisper.cpp / faster-whisper production adapters | Not present | No new dependencies or speculative secondary executor |

## Executor and discovery

`TranscriptionExecutor` exposes capability, transcribe and result validation only.
Production supports the repository-approved `mlx-whisper==0.4.3` Python runtime,
launched with the running application's Python executable in a separate process.
The installed SDK source was inspected for model loading and transcription APIs.
The runtime must import successfully in a bounded child probe; a package or
executable merely existing is not READY. Model load compatibility is separately
probed. ffmpeg and ffprobe use known executable names; no recursive filesystem
search, arbitrary launcher, or model router exists.

Discovery checks the current Python package and configured model directory only.
Model paths are private machine configuration, not transcript identity. Users can
configure an already provisioned model directory through Content diagnostics,
without a terminal. No directory crawling or model marketplace is introduced.

Model identity hashes config bytes plus the full regular weights file (at most
4 GiB), with mutation checks. MLX config is bounded at 64 KiB. Symlink directories,
symlink model files, nonregular files and path traversal are rejected. Both
weights.safetensors and weights.npz are supported as documented by the installed
SDK; no pickle model format is accepted. Capability caches file signatures, then
verifies the content identity again before and after transcription. Missing
assets remain unavailable. No runtime, model weight or dependency is downloaded.

## Capability and operations

Capability distinguishes runtime detected, runtime available, model present,
executor compatible, execution identity and READY. PENDING with
CAPABILITY_CHECKING is a background probe, not executable readiness. Stable job
presentation includes NOT_REQUIRED, PENDING, RUNNING, READY, RUNTIME_UNAVAILABLE,
MODEL_MISSING, UNSUPPORTED, FAILED and INTERRUPTED, localized in zh-CN/en.

Capability checks and transcription run outside the UI request thread. One
application machine slot uses a task-owned file lock shared across processes.
Repeated clicks return the active attempt. Another Content gets a bounded BUSY
result rather than an unbounded queue. Existing jobs and job_attempts record each
explicit attempt; no new scheduler or migration exists. Jobs are admitted as
RUNNING under the owned lock so the existing generic pending-job scheduler cannot
claim them. Maximum attempt lifetime is less than its 35-minute lease.

Retry creates a new attempt and preserves terminal history. The UI submits the
currently visible execution identity; a stale selection is rejected. No executor,
model, language mode or quality fallback occurs. A verified READY transcript is
never replaced by start/retry. If Summary publication was interrupted, the normal
Summary path can be completed without rerunning transcription.

At service startup, reconciliation first acquires the same worker lock; it never
interrupts a live owner. Orphan pending/running attempts become INTERRUPTED and
retryable, never presumed successful. Completed authority is reread independently
of attempt state. No complex cancellation framework is introduced.

## Media and process policy

The imported snapshot is not edited. ffprobe validates the original container.
ffmpeg extracts the first audio stream into a private unique temporary mono
16 kHz PCM WAV under application-controlled machine storage. Audio/video import
limits stay 64 MiB and two hours. The derivative is bounded to two hours of PCM
(about 230 MiB). ffprobe has a 20-second limit, preprocessing 120 seconds, runtime
probe 20 seconds, model-load probe 60 seconds, transcription 30 minutes.

Processes use argument arrays, DEVNULL stdin, isolated process groups and
incrementally drained pipes. stdout is bounded to 4 MiB for a transcript and
64 KiB for tools/probes; stderr has a 64 KiB ceiling. Timeout/output overflow
terminates only the task-owned process group. No stderr, transcript, private path
or stack trace is forwarded to logs/API/UI. Temporary derivatives are removed on
success and failure; unique directories prevent stale reuse/cross-job collision.

On macOS the MLX child is launched with sandbox-exec network denial. SDK downloads
and Python socket connections are also explicitly denied; offline environment
flags are set. ffmpeg/ffprobe allow only file/pipe protocols and disable MOV
external references. No cloud/provider transport is used.

Media-tool discovery resolves the known ffmpeg/ffprobe names only inside existing
trusted installation roots (`/opt/homebrew`, `/usr/local`, `/usr/bin`, `/bin`).
The resolved file must be regular, owned by root/current user, and not writable
by group/others. A matching executable placed in an arbitrary PATH directory is
unavailable rather than executed. Installed media tools remain setup capability;
the product does not install them.

## Transcript authority

MLX seconds normalize once to integer milliseconds by nearest-millisecond
rounding; output that collapses to zero duration is rejected. Segments must be
ordered, nonoverlapping, strictly positive duration, finite, nonnegative and no
more than one second beyond the verified media duration. Bounds: 1–4096 segments,
2000 characters per segment, 2 MiB canonical UTF-8. Empty, malformed, duplicate-key
JSON, invalid encodings, surrogate/control/replacement characters, NaN/infinity,
non-string text and pathological timings fail closed.

Words and whitespace are preserved exactly. No language model cleanup,
translation or invented timestamps exists. Original bounded JSON is retained as
provenance; canonical text is exact cue text joined with newlines. Reliable SDK
source-language output is recorded, otherwise `und` means UNKNOWN. Source,
Summary output and UI languages remain distinct.

Execution identity binds contract, executor implementation, runtime version,
model content digest, source-language mode and decode/profile policy. Attempt
identity also binds Content, whose identity is the immutable source hash.

Phase 7 DATA artifacts, source snapshots, timed rows and Evidence are published
with managed atomic writes and one SQLite transaction. READY is committed only
after the complete source, canonical text, cues and provenance verify inside the
transaction. Orphan files have no authority. Historical envelope v1 stays
supported; v2 binds original executor-output artifact/hash as well. Trusted reread
recomputes source/canonical/raw/timed hashes, verifies ownership and provenance,
revalidates raw timestamps/text and compares normalized segments. Corruption
fails closed before Summary or Evidence consumption.

## Portability and product behavior

Trusted transcript and provenance are portable product authority in DATA and the
existing SQLite archive. Runtime binaries, model weights, paths and temporary
media live outside that archive. Backup/restore verifies the transcript without
probing or requiring any runtime/model. Restored transcripts remain readable;
future transcription may truthfully be unavailable. Schema stays 32 with unchanged
migration lineage/checksums.

Local Content keeps its normal Summary/Evidence/Research surfaces. Timed cues are
shown with source timestamps; concise start/retry status and expandable bounded
diagnostics live in the Transcript panel. No primary navigation is added. Mixed
YouTube + Local timed Evidence uses normal sealed Intelligence dependencies;
Research accepts YouTube + Local text + Local media selected scope. Knowledge
Delta uses ordinary Content completion only, never transcription-engineering
events. No production DA qualification is introduced.

## Provisioning limit

The machine has the approved MLX runtime and media tools, but no compatible MLX
Whisper model in the bounded locations checked. Implementation/isolated execution
validation and real model production validation must be reported separately. A
model download or external installation requires owner provisioning/authorization.

## Review remediation and acceptance refinements

The worker reads and hashes source bytes through managed descriptor storage, then
transcribes a unique verified task-owned copy. Snapshot reopens cannot substitute
media between validation and execution. A process supervisor watches its
application owner and kills only its own isolated group after owner death. Restart
reconciliation and status reads reconcile orphan attempts under the same lock;
bounded cleanup removes only matching task-owned stale directories, without
following symlinks or deleting unrelated storage.

MLX model dimensions are capped at the largest supported Whisper architecture;
NPZ expanded tensor bytes and archive entries are bounded before model loading.
Model-load probes must return the exact compatibility receipt as well as exit 0.
Decode thresholds are explicit, with temperature 0 and no quality/model fallback.

Normal extractive Summary v2 consumes the shared timed candidate builder and
existing Summary Evidence promotion; historical v1 Summary reads remain exact.
Timed citations derive from verified durable millisecond bindings. Local media
Evidence presentation verifies the source/canonical/raw/cue artifacts once in one
read transaction and validates all bounded bindings with the existing cue
validator, avoiding a whole-media hash for every displayed cue. No cache survives
that transaction. Interrupted Summary completion can resume without a runtime or
new transcript. UI completion notification is guarded across Content refreshes.

The design reference is [DESIGN.md](../../DESIGN.md); it records the existing
workspace tokens, localized controls, responsive behavior and disclosure hierarchy.
