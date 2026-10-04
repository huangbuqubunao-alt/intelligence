"""Manual public-video ingestion into shared Following, Content and authority."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from youtube_intel.providers.bilibili import (
    BilibiliAdapter,
    BilibiliError,
    BilibiliMetadata,
    normalize_input,
)
from youtube_intel.research_contract import canonical
from youtube_intel.source_authority import read_managed, sha256, verify_source
from youtube_intel.source_publication import SourceContentPublisher
from youtube_intel.state import (
    ArtifactKind,
    SQLiteStateRepository,
    format_utc_datetime,
)

_IMPORT_LOCK = threading.RLock()


@dataclass(frozen=True)
class NetworkImportResult:
    content_id: str
    status: str
    reused: bool

    def as_dict(self) -> dict[str, object]:
        return {"content_id": self.content_id, "video_id": self.content_id,
                "provider": "BILIBILI", "processing_status": self.status,
                "reused": self.reused}


def metadata_snapshot(metadata: BilibiliMetadata) -> bytes:
    return canonical({"contract": "bilibili-public-metadata-v1",
        "content_id": metadata.identity.content_id, "bvid": metadata.identity.bvid,
        "cid": metadata.cid, "title": metadata.title,
        "uploader_id": metadata.uploader_id, "uploader_name": metadata.uploader_name,
        "published_at": format_utc_datetime(metadata.published_at),
        "duration_seconds": metadata.duration,
        "canonical_url": metadata.identity.canonical_url,
        "acquired_at": format_utc_datetime(metadata.acquired_at)}).encode()


class BilibiliContentProvider(SourceContentPublisher):
    def _source_error(self) -> ValueError:
        return BilibiliError("SOURCE_UNTRUSTED")

    provider = "BILIBILI"
    artifact_namespace = "bilibili"
    producer_version = "bilibili-import-v1"

    def __init__(self, repository: SQLiteStateRepository, data_root: Path, *,
                 adapter: BilibiliAdapter | None = None,
                 now: Callable[[], datetime] | None = None) -> None:
        self.repository = repository
        self.data_root = data_root.absolute()
        repository.bind_source_storage(self.data_root)
        self.adapter = adapter or BilibiliAdapter()
        self.now = now or (lambda: datetime.now(UTC))

    def import_input(self, value: str, *, expected_uploader: str | None = None,
                     following_source_id: str | None = None) -> NetworkImportResult:
        identity = normalize_input(value)
        with _IMPORT_LOCK:
            existing = self.repository.get_video(identity.content_id)
            if existing is not None:
                if expected_uploader is not None:
                    with self.repository._connect() as connection:
                        source = verify_source(self.repository, connection, identity.content_id)
                        artifact = None if source is None else self.repository.get_artifact(source["snapshot_artifact_id"])
                        if artifact is None or json.loads(read_managed(self.data_root, artifact.relative_path, maximum=256 * 1024))["uploader_id"] != expected_uploader:
                            raise BilibiliError("SOURCE_UNTRUSTED")
                return self._existing(identity.content_id)
            metadata = self.adapter.fetch_metadata(identity)
            if expected_uploader is not None and metadata.uploader_id != expected_uploader:
                raise BilibiliError("SOURCE_UNTRUSTED")
            now = self.now()
            timestamp = format_utc_datetime(now)
            payload = metadata_snapshot(metadata)
            digest = sha256(payload)
            source_id = "bilibili-video-" + identity.bvid
            snapshot = self._artifact_write(identity.content_id, "metadata-" + digest + ".json", payload, ArtifactKind.SUBTITLE_SOURCE)
            with self.repository._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                if following_source_id is not None:
                    following = connection.execute("SELECT enabled,channel_id,source_type FROM source_subscriptions WHERE source_id=?", (following_source_id,)).fetchone()
                    if following is None or not following["enabled"] or following["source_type"] != "CREATOR" or following["channel_id"] != metadata.uploader_id:
                        raise BilibiliError("FOLLOWING_PAUSED")
                connection.execute(
                    "INSERT INTO source_subscriptions(source_id,provider,source_type,canonical_url,video_id,display_name,enabled,processing_policy,last_checked_at,last_success_at,created_at,updated_at) VALUES(?,'BILIBILI','VIDEO_URL',?,?,?,1,'DISCOVER_ONLY',?,?,?,?)",
                    (source_id, identity.canonical_url, identity.content_id, metadata.title, timestamp, timestamp, timestamp, timestamp))
                connection.execute(
                    "INSERT INTO videos(video_id,channel_id,title,availability,pipeline_status,pipeline_version,discovered_at,updated_at,provider,duration_seconds,published_at,source_url,channel_name) VALUES(?,?,?,'public','METADATA_READY',?,?,?,'BILIBILI',?,?,?,?)",
                    (identity.content_id, source_id, metadata.title, self.producer_version,
                     timestamp, timestamp, round(metadata.duration), format_utc_datetime(metadata.published_at), identity.canonical_url, metadata.uploader_name))
                connection.execute("INSERT INTO source_video_links(source_id,video_id,discovered_at) VALUES(?,?,?)", (source_id, identity.content_id, timestamp))
                self.repository._upsert_artifact_in_transaction(connection, snapshot, now=timestamp)
                connection.execute(
                    "INSERT INTO content_source_snapshots(content_id,source_id,provider,source_identity,source_hash,snapshot_artifact_id,filename,format,media_kind,byte_count,imported_at,status,duration_seconds) VALUES(?,?,'BILIBILI',?,?,?,?,?,'VIDEO',?,?,'IMPORTED',?)",
                    (identity.content_id, source_id, "bvid:" + identity.bvid, digest,
                     snapshot.artifact_id, metadata.title, ".json", len(payload), timestamp, metadata.duration))
            return self._acquire(metadata, reused=False)

    def _existing(self, content_id: str) -> NetworkImportResult:
        with self.repository._connect() as connection:
            source = verify_source(self.repository, connection, content_id)
            if source is None or source["provider"] != self.provider:
                raise BilibiliError("SOURCE_UNTRUSTED")
            status = str(source["status"])
            language = str(source["language"] or "und")
        if status == "READY":
            self._finish_summary(content_id, self.now(), language)
            with self.repository._connect() as connection:
                connection.execute("UPDATE source_subscriptions SET last_error_code=NULL,last_error_message=NULL,last_success_at=?,updated_at=? WHERE video_id=? AND provider='BILIBILI'", (format_utc_datetime(self.now()), format_utc_datetime(self.now()), content_id))
        return NetworkImportResult(content_id, status, True)

    def retry(self, content_id: str) -> NetworkImportResult:
        with _IMPORT_LOCK:
            current = self._existing(content_id)
            if current.status == "READY":
                return current
            # Reuse the original accepted BV/CID/duration, never mutable live metadata.
            with self.repository._connect() as connection:
                source = verify_source(self.repository, connection, content_id)
                if source is None:
                    raise BilibiliError("SOURCE_UNTRUSTED")
                artifact = self.repository.get_artifact(source["snapshot_artifact_id"])
                if artifact is None:
                    raise BilibiliError("SOURCE_UNTRUSTED")
                doc = json.loads(read_managed(self.data_root, artifact.relative_path, maximum=256 * 1024))
            metadata = BilibiliMetadata(normalize_input(doc["bvid"]), doc["cid"],
                doc["title"], doc["uploader_id"], doc["uploader_name"],
                datetime.fromisoformat(doc["published_at"].replace("Z", "+00:00")),
                doc["duration_seconds"], datetime.fromisoformat(doc["acquired_at"].replace("Z", "+00:00")))
            return self._acquire(metadata, reused=True)

    def _acquire(self, metadata: BilibiliMetadata, *, reused: bool) -> NetworkImportResult:
        caption = self.adapter.fetch_caption(metadata)
        content_id = metadata.identity.content_id
        if caption.transcript is not None:
            assert caption.source_url is not None
            url = urlsplit(caption.source_url)
            self.acquisition = {"provider": self.provider, "bvid": metadata.identity.bvid,
                "cid": metadata.cid, "subtitle_id": caption.subtitle_id,
                "language_name": caption.language_name,
                "source_url": f"https://{url.netloc}{url.path}",
                "acquired_at": format_utc_datetime(self.now())}
            with self.repository._connect() as connection:
                source = verify_source(self.repository, connection, content_id)
                if source is None:
                    raise BilibiliError("SOURCE_UNTRUSTED")
                digest = str(source["source_hash"])
            transcript = caption.transcript
            self._persist_source_result(content_id, "\n".join(c.text for c in transcript.cues),
                transcript, digest, metadata.duration, transcript.language, self.now())
            with self.repository._connect() as connection:
                connection.execute("UPDATE source_subscriptions SET last_error_code=NULL,last_error_message=NULL,last_success_at=?,updated_at=? WHERE video_id=? AND provider='BILIBILI'", (format_utc_datetime(self.now()), format_utc_datetime(self.now()), content_id))
        else:
            with self.repository._connect() as connection:
                connection.execute("UPDATE content_source_snapshots SET status=? WHERE content_id=? AND status!='READY'", (caption.status, content_id))
                connection.execute("UPDATE source_subscriptions SET last_error_code=?,last_error_message=NULL,updated_at=? WHERE video_id=?", (caption.status, format_utc_datetime(self.now()), content_id))
        return NetworkImportResult(content_id, caption.status, reused)
