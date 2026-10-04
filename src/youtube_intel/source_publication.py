"""Shared immutable source publication for Local and public network Providers.

The accepted snapshot, timed transcript, Evidence and Summary contracts own
product authority. Providers acquire data; this service publishes the same domain.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from youtube_intel.source_authority import (
    sha256,
    text_evidence_id,
    verify_source,
    write_managed,
)
from youtube_intel.state import (
    ArtifactKind,
    ArtifactWrite,
    EvidenceAvailability,
    EvidenceLineageKind,
    EvidenceRole,
    EvidenceTextBindingWrite,
    EvidenceWrite,
    RetentionClass,
    SQLiteStateRepository,
    StorageRoot,
    TimedTranscriptWrite,
    build_evidence_id,
    format_utc_datetime,
)

if TYPE_CHECKING:
    from youtube_intel.source_transcript import MediaTranscript


class SourceContentPublisher:
    repository: SQLiteStateRepository
    data_root: Path
    now: Callable[[], datetime]
    provider = "LOCAL"
    artifact_namespace = "local"
    producer_version = "local-import-v1"
    acquisition: dict[str, object] | None = None

    def _source_error(self) -> ValueError:
        return ValueError("source authority is untrusted")

    def _artifact_write(
        self, content_id: str, suffix: str, payload: bytes, kind: ArtifactKind
    ) -> ArtifactWrite:
        digest = sha256(payload)
        artifact_id = f"{content_id}/{suffix}"
        relative = f"transcripts/{self.artifact_namespace}/{content_id}/{suffix}"
        write_managed(self.data_root, relative, payload)
        return ArtifactWrite(
            artifact_id=artifact_id,
            artifact_key=artifact_id,
            video_id=content_id,
            job_id=None,
            kind=kind,
            storage_root=StorageRoot.DATA,
            relative_path=relative,
            content_hash=digest,
            provider=self.provider,
            model=None,
            producer_version=self.producer_version,
            retention_class=RetentionClass.LONG_LIVED,
            expires_at=None,
        )

    def _persist_source_result(self, content_id: str, text: str, transcript: MediaTranscript | None,
                               digest: str, duration: float | None, language: str, now: datetime) -> None:
        timestamp = format_utc_datetime(now)
        canonical = self._artifact_write(
            content_id,
            "canonical.txt" if transcript is None else f"canonical-{sha256(text.encode())}.txt",
            text.encode("utf-8"),
            ArtifactKind.TRANSCRIPT_CANONICAL,
        )
        provenance = None
        raw_artifact = None
        if transcript is not None and transcript.raw_output is not None:
            raw_name = "source-caption" if self.provider == "BILIBILI" else "executor-output"
            raw_artifact = self._artifact_write(content_id, f"{raw_name}-{sha256(transcript.raw_output)}.json", transcript.raw_output, ArtifactKind.SUBTITLE_SOURCE)
        if transcript is not None:
            timed = TimedTranscriptWrite.from_cues(
                video_id=content_id,
                canonical_artifact_id=canonical.artifact_id,
                cues=transcript.cues,
            )
            from youtube_intel.research_contract import canonical as canonical_json

            envelope = canonical_json(
                {
                    "contract": "source-transcript-provenance-v1" if raw_artifact is None else ("source-transcript-provenance-v3" if self.provider == "BILIBILI" else "source-transcript-provenance-v2"),
                    **({"acquisition": self.acquisition} if self.provider == "BILIBILI" else {}),
                    **({} if raw_artifact is None else {"raw_artifact_id": raw_artifact.artifact_id, "raw_output_hash": raw_artifact.content_hash}),
                    "content_id": content_id,
                    "source_hash": digest,
                    "canonical_text_hash": sha256(text.encode("utf-8")),
                    "timed_transcript_hash": timed.timed_transcript_hash,
                    "language": language,
                    "duration_seconds": duration,
                    "transcriber": transcript.provenance,
                }
            ).encode("utf-8")
            provenance = self._artifact_write(
                content_id,
                f"transcript-provenance-{sha256(envelope)}.json",
                envelope,
                ArtifactKind.SUBTITLE_SOURCE,
            )
        with self.repository._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            source = verify_source(self.repository, connection, content_id)
            if source is None or source["source_hash"] != digest:
                raise self._source_error()
            if source["status"] == "READY":
                return
            if raw_artifact is not None:
                self.repository._upsert_artifact_in_transaction(connection, raw_artifact, now=timestamp)
            self.repository._upsert_artifact_in_transaction(
                connection, canonical, now=timestamp
            )
            if provenance is not None:
                self.repository._upsert_artifact_in_transaction(
                    connection, provenance, now=timestamp
                )
                connection.execute(
                    "UPDATE content_source_snapshots SET provenance_artifact_id=? WHERE content_id=?",
                    (provenance.artifact_id, content_id),
                )
            connection.execute(
                "UPDATE content_source_snapshots SET canonical_artifact_id=?,canonical_text=?,canonical_text_hash=?,language=?,transcript_provenance=? WHERE content_id=?",
                (
                    canonical.artifact_id,
                    text,
                    sha256(text.encode("utf-8")),
                    language,
                    "utf-8-exact-v1"
                    if transcript is None
                    else transcript.provenance,
                    content_id,
                ),
            )
            if transcript is None:
                self._text_evidence(
                    connection, content_id, canonical.artifact_id, text, digest, now
                )
            else:
                self._media_evidence(
                    connection, content_id, canonical.artifact_id, transcript, now
                )
            connection.execute(
                "UPDATE content_source_snapshots SET status='READY' WHERE content_id=?",
                (content_id,),
            )
            connection.execute("UPDATE videos SET default_language=? WHERE video_id=?", (language, content_id))
            if verify_source(self.repository, connection, content_id) is None:
                raise self._source_error()
        self._finish_summary(content_id, now, language)

    def _finish_summary(self, content_id: str, now: datetime, language: str) -> None:
        from youtube_intel.extractive_summary import ExtractiveSummaryService

        pointer = self.repository.current_local_summary_pointer(content_id)
        if pointer is None:
            ExtractiveSummaryService(self.repository, self.data_root).create(
                content_id, now=now
            )
        timestamp = format_utc_datetime(now)
        with self.repository._connect() as connection:
            connection.execute(
                "UPDATE videos SET pipeline_status='COMPLETE',completed_at=COALESCE(completed_at,?),updated_at=?,default_language=? WHERE video_id=? AND pipeline_status!='COMPLETE'",
                (timestamp, timestamp, language, content_id),
            )

    def _text_evidence(
        self,
        connection: sqlite3.Connection,
        content_id: str,
        artifact_id: str,
        text: str,
        source_hash: str,
        now: datetime,
    ) -> None:
        offset = 0
        # Ordinary text retains line-level excerpts. Highly fragmented input
        # uses bounded exact windows, preventing millions of evidence rows.
        lines = text.splitlines(keepends=True)
        parts = (
            lines
            if len(lines) <= 2048
            else [text[i : i + 1000] for i in range(0, len(text), 1000)]
        )
        canonical_hash = sha256(text.encode("utf-8"))
        for line in parts:
            for index in range(0, len(line), 1000):
                excerpt = line[index : index + 1000]
                start = offset + index
                end = start + len(excerpt)
                if not excerpt.strip():
                    continue
                eid = text_evidence_id(
                    content_id=content_id,
                    artifact_id=artifact_id,
                    start_offset=start,
                    end_offset=end,
                )
                connection.execute(
                    "INSERT INTO evidence(evidence_id,video_id,artifact_id,locator_type,start_offset,end_offset,lineage_kind,role,language,availability,created_at,source_excerpt) VALUES(?,?,?,'TEXT_RANGE',?,?,'ORIGINAL_TRANSCRIPT','PRIMARY_ORIGINAL','und','AVAILABLE',?,?)",
                    (
                        eid,
                        content_id,
                        artifact_id,
                        start,
                        end,
                        format_utc_datetime(now),
                        excerpt,
                    ),
                )
                connection.execute(
                    "INSERT INTO evidence_source_ranges VALUES(?,?,?,?,?,?)",
                    (
                        eid,
                        artifact_id,
                        excerpt,
                        sha256(excerpt.encode("utf-8")),
                        canonical_hash,
                        source_hash,
                    ),
                )
            offset += len(line)

    def _media_evidence(
        self,
        connection: sqlite3.Connection,
        content_id: str,
        artifact_id: str,
        transcript: MediaTranscript,
        now: datetime,
    ) -> None:
        timed = TimedTranscriptWrite.from_cues(
            video_id=content_id, canonical_artifact_id=artifact_id, cues=transcript.cues
        )
        timestamp = format_utc_datetime(now)
        connection.execute(
            "INSERT INTO timed_transcripts(timed_transcript_id,video_id,canonical_artifact_id,timed_transcript_hash,created_at) VALUES(?,?,?,?,?)",
            (
                timed.timed_transcript_id,
                content_id,
                artifact_id,
                timed.timed_transcript_hash,
                timestamp,
            ),
        )
        connection.executemany(
            "INSERT INTO timed_transcript_cues(timed_transcript_id,cue_index,start_ms,end_ms,cue_text,cue_text_hash) VALUES(?,?,?,?,?,?)",
            [
                (
                    timed.timed_transcript_id,
                    index,
                    c.start_ms,
                    c.end_ms,
                    c.text,
                    c.text_hash,
                )
                for index, c in enumerate(transcript.cues)
            ],
        )
        for index, cue in enumerate(transcript.cues):
            eid = build_evidence_id(
                video_id=content_id,
                artifact_id=artifact_id,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
                role=EvidenceRole.PRIMARY_ORIGINAL,
            )
            evidence = EvidenceWrite(
                evidence_id=eid,
                video_id=content_id,
                artifact_id=artifact_id,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                lineage_kind=EvidenceLineageKind.ORIGINAL_TRANSCRIPT,
                role=EvidenceRole.PRIMARY_ORIGINAL,
                language=transcript.language,
                availability=EvidenceAvailability.AVAILABLE,
                source_excerpt=cue.text,
            )
            binding = EvidenceTextBindingWrite.from_timed_transcript(
                evidence=evidence,
                timed_transcript_id=timed.timed_transcript_id,
                start_cue_index=index,
                end_cue_index=index + 1,
                excerpt=cue.text,
            )
            connection.execute(
                "INSERT INTO evidence(evidence_id,video_id,artifact_id,start_ms,end_ms,lineage_kind,role,language,availability,created_at,source_excerpt) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    eid,
                    content_id,
                    artifact_id,
                    cue.start_ms,
                    cue.end_ms,
                    evidence.lineage_kind.value,
                    evidence.role.value,
                    transcript.language,
                    evidence.availability.value,
                    timestamp,
                    cue.text,
                ),
            )
            self.repository._insert_evidence_text_binding_in_transaction(
                connection, evidence, binding, now=now
            )
