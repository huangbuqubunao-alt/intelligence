# D2-02 Native Local Import

Authoritative base: c990e698c9e0c5f3ea65e62c8ecfde09db60556b. One task, one writer;
owner explicitly authorized the narrow Schema 36 size-check migration and the
native picker / launcher integration. No production dependencies are added.

## Reuse decision

DIRECT: Apple's AppKit NSOpenPanel, installed clang and SDK, APFS fclonefileat;
Python standard-library descriptor I/O, hashlib, threading, zipfile and SQLite;
existing SourceContentPublisher, offline-only transcription and React components.
REFERENCE: Apple clonefile and NSOpenPanel documentation. Cloud upload frameworks
are REJECT/DEFER: the application and selected source are on the same Mac.

## Native authorization and snapshot

macOS UI sends only `{}` controls to the exact launcher origin. A fixed one-shot
AppKit helper with no arguments presents a real user selection. Paths never enter
HTTP requests or public job responses. Grant descriptors open through a no-follow
ancestor walk, validate regular files and retain inode/size/mtime/ctime. Random
one-use job grants are origin-bound and expire after ten minutes. Native controls
require exact loopback Origin and Host, local-ui request header and same-origin
fetch metadata. No CORS and no caller path/script API are exposed.

Confirmation returns immediately and runs off the request/UI thread. Same-volume
APFS clone uses an authorized descriptor into private staging; the original is
never written. Unsupported clone or different volumes use 1 MiB streamed copying
with actual byte progress. Reserve the full declared size plus 256 MiB even for
CoW. Pin the clone, fsync it, stream SHA-256, probe format and duration, validate
again and atomically publish without replacing existing snapshots. Maintain
local-sha256 identity, original-filename provenance and authoritative Evidence.
Copies changed before publication fail closed. Successful snapshots have a
separate inode and remain valid after source edits/moves/deletion.

Media limit: inclusive 2 GiB. TXT/MD: 2 MiB. Duration: unchanged 7200 seconds,
with a distinct duration error. No provisional Content identity is invented before
SHA verification: the pending job is visible immediately; verified Content appears
as soon as admission commits. Success automatically opens Content. Saved-file
status and transcription/summary status stay distinct. Pending work remains
visible outside the dialog, with a continue-in-background control.

## Bounded data chain and recovery

Existing HTTP compatibility admission, source verification, offline-attempt copy,
backup packing/download, restore staging/extraction/activation all stream bounded
chunks. macOS primary UI has no browser file input and does not fall back to HTTP
upload when native authorization is unavailable. Existing non-macOS adapter remains
compatible. Do not present legacy HTTP validation as proof of native zero upload.

Private nonces and inode-aware cleanup never overwrite/delete existing snapshots.
Cancellation, idle/total timeouts, disk exhaustion and failed admission have clear
codes. Startup cleanup locks directories and skips live import stages. Native
publication gates backup/restore against partial snapshots.

ZIP64 uses stored media to avoid rejecting its own compressible/sparse snapshots.
Archive and aggregate expanded limits: 8 GiB; individual DATA member: 2 GiB;
manifest/central-directory metadata are bounded. Reserve packing/extraction/copy
space using actual filesystems, retain hash/path/type/schema/authority checks and
rollback state. Admission refuses libraries exceeding safe backup capacity.

## Evidence policy

Real 2 GiB files are ffmpeg one-second valid MP4s padded by a valid sparse free
atom. Their full bytes are hashed, snapshotted, backed up and restored. First native
selection is real AppKit; later near-boundary/dedupe/forced-fallback cases explicitly
use test seams. No ASR or paid model is called: timed Evidence is deterministic,
owned by the isolated fixture. Forced unsupported-clone fallback is a real 2 GiB
copy but does not represent an actual external non-APFS disk. Size/time/disk error
boundaries are separately simulated. Tests never use the owner's database.
